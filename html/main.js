const API_BASE_URL = 'http://localhost:8000'; // 假设后端运行在 8000 端口
let currentThreadId = null;
let pollInterval = null;
let previousStatus = null;

// 配置 marked.js 以支持 TOC 跳转 (自动添加标题 ID) 和 链接新窗口打开
const renderer = {
    heading(text, level) {
        // 改进的 Slug 生成逻辑：模拟 GitHub/Python-Markdown 风格
        // Primary ID: en-dash/em-dash -> hyphen
        const id = text
            .toLowerCase()
            .replace(/[\u2013\u2014]/g, '-') 
            .replace(/\s+/g, '-')
            .replace(/[^\w\u4e00-\u9fa5\-]+/g, '')
            .replace(/\-\-+/g, '-')
            .replace(/^-+|-+$/g, '');
        
        // Alternative ID 1: Remove en-dash/em-dash (don't replace with hyphen)
        const idNoDash = text
            .toLowerCase()
            .replace(/\s+/g, '-')
            .replace(/[^\w\u4e00-\u9fa5\-]+/g, '') // Removes en-dash/em-dash
            .replace(/\-\-+/g, '-')
            .replace(/^-+|-+$/g, '');

        // Alternative ID 2: Keep en-dash/em-dash
        const idKeepDash = text
            .toLowerCase()
            .replace(/\s+/g, '-')
            .replace(/[^\w\u4e00-\u9fa5\-\u2013\u2014]+/g, '') // Keeps en-dash/em-dash
            .replace(/\-\-+/g, '-')
            .replace(/^-+|-+$/g, '');

        // Alternative ID 3: Keep parenthesis (full-width and half-width)
        const idKeepParen = text
            .toLowerCase()
            .replace(/[\u2013\u2014]/g, '-') 
            .replace(/\s+/g, '-')
            .replace(/[^\w\u4e00-\u9fa5\-\(\)（）]+/g, '') // Keep parenthesis
            .replace(/\-\-+/g, '-')
            .replace(/^-+|-+$/g, '');

        // Alternative ID 4: Keep parenthesis AND en-dash
        const idKeepAll = text
            .toLowerCase()
            .replace(/\s+/g, '-')
            .replace(/[^\w\u4e00-\u9fa5\-\(\)（）\u2013\u2014]+/g, '') 
            .replace(/\-\-+/g, '-')
            .replace(/^-+|-+$/g, '');

        // Generate hidden anchors for compatibility
        let anchors = '';
        if (idNoDash !== id) anchors += `<a id="${idNoDash}" class="anchor-offset"></a>`;
        if (idKeepDash !== id && idKeepDash !== idNoDash) anchors += `<a id="${idKeepDash}" class="anchor-offset"></a>`;
        if (idKeepParen !== id && idKeepParen !== idNoDash && idKeepParen !== idKeepDash) anchors += `<a id="${idKeepParen}" class="anchor-offset"></a>`;
        if (idKeepAll !== id && idKeepAll !== idNoDash && idKeepAll !== idKeepDash && idKeepAll !== idKeepParen) anchors += `<a id="${idKeepAll}" class="anchor-offset"></a>`;
            
        return `<h${level} id="${id}">${anchors}${text}</h${level}>`;
    },
    link(href, title, text) {
        const isInternal = href && href.startsWith('#');
        const targetAttr = isInternal ? '' : 'target="_blank" rel="noopener noreferrer"';
        return `<a href="${href}" title="${title || ''}" ${targetAttr}>${text}</a>`;
    }
};

// 检查 marked 版本兼容性
if (typeof marked.use === 'function') {
    marked.use({ renderer });
}

document.addEventListener('DOMContentLoaded', () => {
    // Helper to safely add listener
    const addListener = (id, event, handler) => {
        const el = document.getElementById(id);
        if (el) el.addEventListener(event, handler);
    };

    // Event Listeners
    addListener('start-btn', 'click', startResearch);
    addListener('approve-plan-btn', 'click', () => submitFeedback(true));
    addListener('reject-plan-btn', 'click', toggleFeedbackInput);
    addListener('submit-feedback-btn', 'click', () => submitFeedback(false));
    addListener('download-pdf-btn', 'click', downloadPDF);
});

async function startResearch() {
    const query = document.getElementById('query').value.trim();
    const maxSteps = parseInt(document.getElementById('max-steps').value, 10);

    if (!query) {
        alert('请输入研究主题');
        return;
    }

    // UI Update
    document.getElementById('input-section').classList.add('hidden');
    document.getElementById('status-section').classList.remove('hidden');
    addLog('正在初始化研究 Agent...');

    try {
        // Update endpoint path and ensure payload structure matches backend ResearchRequest
        const response = await fetch(`${API_BASE_URL}/research`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: query,
                // Assuming backend allows flexible config or ignores extras
                // We can map max_steps to config if supported, but for now keeping simple
                // Or if we want to be strict:
                config: {
                    require_plan_approval: true,
                    max_search_iterations: maxSteps || 5
                }
            })
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(errData.detail || 'Start failed');
        }
        const data = await response.json();
        currentThreadId = data.session_id;
        
        addLog(`研究会话已创建: ${currentThreadId}`);
        startPolling();

    } catch (error) {
        console.error(error);
        addLog(`错误: 无法启动研究任务 - ${error.message}`, 'error');
        alert(`启动失败: ${error.message}\n请检查后端服务是否运行，以及是否配置了正确的 API Key`);
        document.getElementById('input-section').classList.remove('hidden');
        document.getElementById('status-section').classList.add('hidden');
    }
}

function startPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
    }
    
    // 使用标准函数表达式以避免可能的解析问题
    pollInterval = setInterval(function() {
        checkStatus();
    }, 2000);
}

async function checkStatus() {
    if (!currentThreadId) return;

    try {
        const response = await fetch(`${API_BASE_URL}/research/${currentThreadId}/status`);
        const state = await response.json();

        updateStatusDisplay(state);
        handleStateLogic(state);

    } catch (error) {
        console.error('Polling error', error);
        // Don't stop polling immediately on one error, but maybe log it
    }
}

function updateStatusDisplay(state) {
    const statusBadge = document.getElementById('status-badge');
    const progressBar = document.getElementById('progress-bar');
    const progressContainer = document.getElementById('progress-container');
    
    statusBadge.textContent = state.status || 'UNKNOWN';
    statusBadge.className = `badge ${state.status?.toLowerCase() || 'pending'}`;

    if (state.status !== previousStatus) {
        addLog(`状态更新: ${state.status}`);
        previousStatus = state.status;
    }

    // Progress logic (simplified)
    progressContainer.classList.remove('hidden');
    
    let progress = 0;
    if (state.status === 'planning') progress = 10;
    else if (state.status === 'plan_review') progress = 20;
    else if (state.status === 'executing') {
        progress = 30;
        // If we have step info
        if (state.research_plan && state.research_plan.steps) {
            const total = state.research_plan.steps.length;
            const current = state.extracted_insights ? Object.keys(state.extracted_insights).length : 0;
            const stepProgress = (current / total) * 60; // 30% -> 90%
            progress = 30 + stepProgress;
        }
    }
    else if (state.status === 'completed') progress = 100;
    
    progressBar.style.width = `${progress}%`;
}

function handleStateLogic(state) {
    // Handle Plan Approval
    if (state.status === 'plan_review' && state.waiting_for_approval) {
        document.getElementById('plan-section').classList.remove('hidden');
        
        // Render Plan
        const planContentDiv = document.getElementById('plan-content');
        
        if (state.research_plan) {
            // Debug Log
            if (!planContentDiv.hasAttribute('data-rendered')) {
                 console.log("Rendering plan:", state.research_plan);
                 const stepCount = state.research_plan.steps ? state.research_plan.steps.length : 0;
                 addLog(`收到研究计划: ${stepCount} 个步骤`);
                 planContentDiv.setAttribute('data-rendered', 'true');
            }

            // Manual HTML Construction to avoid Markdown/CDN dependencies
            let planHtml = "";
            try {
                planHtml += `<div class="mb-3"><strong>🎯 研究目标:</strong> ${state.research_plan.objective || '无目标'}</div>`;
                
                const steps = Array.isArray(state.research_plan.steps) ? state.research_plan.steps : [];
                if (steps.length === 0) {
                     planHtml += `<div class="alert alert-warning">注意：计划中没有步骤数据。</div>`;
                     planHtml += `<pre class="small text-muted">${JSON.stringify(state.research_plan, null, 2)}</pre>`;
                } else {
                    planHtml += `<div class="steps-list">`;
                    steps.forEach((s, i) => {
                         planHtml += `
                            <div class="step-item p-2 border-bottom">
                                <div class="fw-bold">步骤 ${i+1}: ${s.title || 'Untitled'}</div>
                                <div class="text-muted small">${s.description || ''}</div>
                                ${s.expected_output ? `<div class="text-info x-small">Expected: ${s.expected_output}</div>` : ''}
                            </div>
                         `;
                    });
                    planHtml += `</div>`;
                    planHtml += `<div class="mt-3 text-muted small">Estimated duration: ${state.research_plan.estimated_duration_minutes || '?'} mins</div>`;
                }
            } catch (e) {
                console.error("Error constructing plan HTML:", e);
                planHtml = `<div class="text-danger">Error render plan: ${e.message}</div>`;
            }

            planContentDiv.innerHTML = planHtml;
        } else {
            planContentDiv.innerHTML = `<div class="notice error">
                未找到研究计划数据 (research_plan is null)。<br>
                请检查后端日志。
                <br>State Dump: <pre>${JSON.stringify(state, null, 2)}</pre>
            </div>`;
        }
    } else {
        document.getElementById('plan-section').classList.add('hidden');
        // Clear rendered flag when hidden
        const planContentDiv = document.getElementById('plan-content');
        if(planContentDiv) planContentDiv.removeAttribute('data-rendered');
    }

    // Handle Final Report
    if (state.status === 'completed' && state.final_report) {
        if (pollInterval) clearInterval(pollInterval);
        document.getElementById('report-section').classList.remove('hidden');
        
        // Use marked for report as it is pure markdown
        try {
            console.log("Rendering report, length:", state.final_report.length);
            if (typeof marked !== 'undefined' && typeof marked.parse === 'function') {
                 document.getElementById('report-content').innerHTML = marked.parse(state.final_report);
            } else if (typeof marked === 'function') {
                 // Fallback for older marked versions
                 document.getElementById('report-content').innerHTML = marked(state.final_report);
            } else {
                 // Fallback if marked is not loaded
                 addLog("Warning: marked.js not loaded, showing raw text", "warning");
                 document.getElementById('report-content').textContent = state.final_report;
            }
            addLog('✅ 研究任务完成！');
        } catch (e) {
            console.error("Error rendering report:", e);
            addLog(`Error rendering report: ${e.message}`, 'error');
            document.getElementById('report-content').textContent = state.final_report;
        }
    }
}

function toggleFeedbackInput() {
    document.getElementById('feedback-input').classList.toggle('hidden');
}

async function submitFeedback(isApproved) {
    const feedback = document.getElementById('plan-feedback').value;
    
    try {
        addLog('正在提交反馈...');
        const response = await fetch(`${API_BASE_URL}/research/${currentThreadId}/feedback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: currentThreadId,
                feedback: {
                    action: isApproved ? "approve" : "modify",
                    notes: feedback || "User requested changes"
                }
            })
        });
        
        if (response.ok) {
            addLog('反馈提交成功，继续运行...');
            document.getElementById('plan-section').classList.add('hidden');
            // Status will update on next poll
        } else {
            addLog('反馈提交失败', 'error');
        }
    } catch (e) {
        console.error(e);
        addLog('反馈提交错误', 'error');
    }
}

function addLog(message, type = 'info') {
    const logs = document.getElementById('logs-container');
    const entry = document.createElement('div');
    entry.className = `log-entry ${type === 'error' ? 'text-danger' : ''}`;
    const time = new Date().toLocaleTimeString();
    entry.textContent = `[${time}] ${message}`;
    logs.appendChild(entry);
    logs.scrollTop = logs.scrollHeight;
}

function downloadPDF() {
    const originalElement = document.getElementById('report-content');
    if (!originalElement || !originalElement.innerHTML) {
        alert('没有可下载的报告内容');
        return;
    }

    addLog('正在准备 PDF 生成...');

    // Create a clone of the element to avoid messing with the live view
    // and to ensure we can control the rendering environment completely
    const clone = originalElement.cloneNode(true);
    
    // Create a container for the clone
    const container = document.createElement('div');
    container.style.position = 'fixed'; // Use fixed to ensure it's relative to viewport but hidden
    container.style.left = '-10000px'; // Move far left instead of top
    container.style.top = '0';
    container.style.width = '800px'; // Slightly wider to accommodate margins
    container.style.backgroundColor = 'white';
    container.style.zIndex = '-9999';
    
    // Apply the export class to the clone
    clone.classList.add('pdf-export-mode');
    
    // Ensure clone is visible and has auto height
    clone.style.width = '100%'; // Fill container
    clone.style.height = 'auto';
    clone.style.overflow = 'visible';
    clone.style.maxHeight = 'none';

    // Add padding buffer to clone to prevent bottom cut-off
    const paddingDiv = document.createElement('div');
    paddingDiv.style.height = '50px';
    paddingDiv.style.clear = 'both';
    clone.appendChild(paddingDiv);

    container.appendChild(clone);
    document.body.appendChild(container);

    // Wait a brief moment for layout to settle
    setTimeout(() => {
        // Debug: Check width
        console.log('PDF Container Width:', container.offsetWidth);
        console.log('PDF Clone Width:', clone.offsetWidth);

        const opt = {
            margin:       [10, 10, 10, 10], // Top, Right, Bottom, Left
            filename:     `Research_Report_${currentThreadId || 'doc'}.pdf`,
            image:        { type: 'jpeg', quality: 0.98 },
            html2canvas:  { 
                scale: 2, 
                useCORS: true, 
                letterRendering: true,
                width: 800, // Explicitly set width
                windowWidth: 800, // Match container width
                scrollY: 0,
                x: 0,
                y: 0
            },
            jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' },
            // 'avoid-all' can cause large gaps if elements are long. 
            // Using 'css' allows us to control breaks via classes like .page-break-inside-avoid
            pagebreak:    { mode: ['css', 'legacy'] } 
        };

        if (typeof html2pdf !== 'undefined') {
            addLog('正在生成 PDF...');
            html2pdf().set(opt).from(clone).save().then(() => {
                addLog('PDF 下载完成');
                document.body.removeChild(container);
            }).catch(err => {
                console.error(err);
                addLog('PDF 生成失败', 'error');
                document.body.removeChild(container);
            });
        } else {
            alert('PDF 生成库未加载，请检查网络连接');
            document.body.removeChild(container);
        }
    }, 100);
}
