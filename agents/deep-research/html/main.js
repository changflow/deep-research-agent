const API_BASE_URL = 'http://localhost:8000';
let currentThreadId = null;
let pollInterval = null;
let previousStatus = null;
let isRegeneratingPlan = false; // Flag to track plan regeneration after feedback

// Configure marked.js
const renderer = {
    heading(text, level) {
        const id = text
            .toLowerCase()
            .replace(/[\u2013\u2014]/g, '-') 
            .replace(/\s+/g, '-')
            .replace(/[^\w\u4e00-\u9fa5\-]+/g, '')
            .replace(/\-\-+/g, '-')
            .replace(/^-+|-+$/g, '');
        return `<h${level} id="${id}">${text}</h${level}>`;
    },
    link(href, title, text) {
        const isInternal = href && href.startsWith('#');
        const targetAttr = isInternal ? '' : 'target="_blank" rel="noopener noreferrer"';
        return `<a href="${href}" title="${title || ''}" ${targetAttr}>${text}</a>`;
    }
};

if (typeof marked !== 'undefined' && typeof marked.use === 'function') {
    marked.use({ renderer });
}

document.addEventListener('DOMContentLoaded', () => {
    const addListener = (id, event, handler) => {
        const el = document.getElementById(id);
        if (el) el.addEventListener(event, handler);
    };

    addListener('start-btn', 'click', startResearch);
    addListener('approve-plan-btn', 'click', () => submitFeedback(true));
    addListener('reject-plan-btn', 'click', toggleFeedbackInput);
    addListener('submit-feedback-btn', 'click', () => submitFeedback(false));
    addListener('download-pdf-btn', 'click', downloadPDF);
    addListener('toggle-mindmap-btn', 'click', toggleMindMap);
});

function toggleMindMap() {
    console.log("Toggle MindMap clicked");
    const container = document.getElementById('mind-map-container');
    const btn = document.getElementById('toggle-mindmap-btn');
    if (!container || !btn) {
        console.error("Missing elements for toggle");
        return;
    }
    container.classList.toggle('collapsed');
    const isCollapsed = container.classList.contains('collapsed');
    btn.textContent = isCollapsed ? '展开 v' : '收起 ^';
}

async function startResearch() {
    const query = document.getElementById('query').value.trim();
    const maxSteps = parseInt(document.getElementById('max-steps').value, 10);

    if (!query) {
        alert('请输入研究主题');
        return;
    }

    document.getElementById('input-section').classList.add('hidden');
    document.getElementById('status-section').classList.remove('hidden');
    addLog('正在初始化研究 Agent...');

    try {
        const response = await fetch(`${API_BASE_URL}/research`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: query,
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
        alert(`启动失败: ${error.message}`);
        document.getElementById('input-section').classList.remove('hidden');
        document.getElementById('status-section').classList.add('hidden');
    }
}

function startPolling() {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(checkStatus, 2000);
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

    progressContainer.classList.remove('hidden');
    
    let progress = 0;
    if (state.status === 'planning') progress = 10;
    else if (state.status === 'plan_review') progress = 20;
    else if (state.status === 'executing') {
        progress = 30;
        if (state.research_plan && state.research_plan.steps) {
            const total = state.research_plan.steps.length;
            const current = state.extracted_insights ? Object.keys(state.extracted_insights).length : 0;
            const stepProgress = total > 0 ? (current / total) * 60 : 0;
            progress = 30 + stepProgress;
        }
    }
    else if (state.status === 'completed') progress = 100;
    
    progressBar.style.width = `${progress}%`;
}

function handleStateLogic(state) {
    // 1. Update MindMap Data First (DOM content only)
    updateMindMap(state);

    const planSection = document.getElementById('plan-section');
    const vizSection = document.getElementById('visualization-section');
    const reportSection = document.getElementById('report-section');

    const isPlanReview = (state.status || '').toLowerCase() === 'plan_review';
    const isPending = state.status === 'pending';
    const isExecuting = (state.status || '').toLowerCase() === 'executing';
    const hasPlan = !!state.research_plan;
    // Check waiting_for_approval if the backend provides it, otherwise assume true if in plan_review
    const isWaitingApproval = state.waiting_for_approval !== false; 

    // Clear regeneration flag if we enter plan_review (new plan ready) or executing (approved)
    if (isPlanReview || isExecuting) {
        isRegeneratingPlan = false;
    }

    // 2. Handle Plan Approval Section UI
    // Only show approval UI if in plan_review AND waiting for approval
    // Critical: If regenerating, do NOT show approval UI even if status says plan_review (prevents race conditions)
    const showPlanApproval = isPlanReview && isWaitingApproval && !isRegeneratingPlan;
    
    // Manage Plan Section Visibility
    if (showPlanApproval) {
        planSection.classList.remove('hidden');
        
        // Ensure approval elements are visible (in case they were hidden during regeneration)
        const noticeEl = planSection.querySelector('.notice');
        const actionsEl = planSection.querySelector('.actions');
        if (noticeEl) noticeEl.classList.remove('hidden');
        if (actionsEl) actionsEl.classList.remove('hidden');
        
        // Render Plan Content
        const planContentDiv = document.getElementById('plan-content');
        if (state.research_plan) {
            if (!planContentDiv.hasAttribute('data-rendered')) {
                 const stepCount = state.research_plan.steps ? state.research_plan.steps.length : 0;
                 addLog(`收到研究计划: ${stepCount} 个步骤，等待审批`);
                 planContentDiv.setAttribute('data-rendered', 'true');
            }
            renderPlanContent(state.research_plan, planContentDiv);
            
            // Clear any loading state message if it exists
            const existingMsg = document.getElementById('plan-regen-msg');
            if (existingMsg) existingMsg.remove();
        }
    } else if (isRegeneratingPlan) {
        // KEEP plan section visible but show loading message
        // HIDE approval buttons and notice as requested by user
        
        planSection.classList.remove('hidden');
        
        const noticeEl = planSection.querySelector('.notice');
        const actionsEl = planSection.querySelector('.actions');
        if (noticeEl) noticeEl.classList.add('hidden');
        if (actionsEl) actionsEl.classList.add('hidden');

        const planContentDiv = document.getElementById('plan-content');
        planContentDiv.innerHTML = '<div id="plan-regen-msg" class="alert alert-info">🔄 正在根据您的反馈重新生成计划，请稍候...</div>';
    } else {
        planSection.classList.add('hidden');
        const planContentDiv = document.getElementById('plan-content');
        if(planContentDiv) planContentDiv.removeAttribute('data-rendered');
    }

    // 3. Handle Visualization Section Visibility
    // User Requirement: "由于 plan_review 状态下要先审批，所以思维过程在这个阶段不应展示，确认后再展示"
    // New Requirement: Also hide when regenerating plan to avoid showing old plan data.
    // Logic: Show visualization if we have a plan, NOT pending, NOT showing approval section, AND NOT regenerating.
    // Update: Also hide if status is 'planning' (prevent showing old map during regeneration)
    const isPlanning = (state.status || '').toLowerCase() === 'planning';
    const shouldShowVisualization = hasPlan && !isPending && !showPlanApproval && !isRegeneratingPlan && !isPlanning;

    if (shouldShowVisualization) {
        vizSection.classList.remove('hidden');
    } else {
        vizSection.classList.add('hidden');
    }

    // 4. Handle Final Report
    if (state.status === 'completed' && state.final_report) {
        if (pollInterval) clearInterval(pollInterval);
        reportSection.classList.remove('hidden');
        renderReport(state.final_report);
        addLog('✅ 研究任务完成！');
    }
}

function renderPlanContent(plan, container) {
    let html = "";
    try {
        html += `<div class="mb-3"><strong>🎯 研究目标:</strong> ${plan.objective || '无目标'}</div>`;
        const steps = Array.isArray(plan.steps) ? plan.steps : [];
        if (steps.length === 0) {
             html += `<div class="alert alert-warning">注意：计划中没有步骤数据。</div>`;
        } else {
            html += `<div class="steps-list">`;
            steps.forEach((s, i) => {
                 html += `
                    <div class="step-item p-2 border-bottom">
                        <div class="fw-bold">步骤 ${i+1}: ${s.title || 'Untitled'}</div>
                        <div class="text-muted small">${s.description || ''}</div>
                        ${s.expected_output ? `<div class="text-info x-small">Expected: ${s.expected_output}</div>` : ''}
                    </div>
                 `;
            });
            html += `</div>`;
            html += `<div class="mt-3 text-muted small">预计耗时: ${plan.estimated_duration_minutes || '?'} 分钟</div>`;
        }
    } catch (e) {
        console.error("Error constructing plan HTML:", e);
        html = `<div class="text-danger">渲染计划出错: ${e.message}</div>`;
    }
    container.innerHTML = html;
}

function renderReport(markdownText) {
    const container = document.getElementById('report-content');
    try {
        if (typeof marked !== 'undefined' && typeof marked.parse === 'function') {
             container.innerHTML = marked.parse(markdownText);
        } else if (typeof marked === 'function') {
             container.innerHTML = marked(markdownText);
        } else {
             container.textContent = markdownText;
        }
    } catch (e) {
        console.error("Error rendering report:", e);
        container.textContent = markdownText;
    }
}

function toggleFeedbackInput() {
    document.getElementById('feedback-input').classList.toggle('hidden');
}

async function submitFeedback(isApproved) {
    const feedback = document.getElementById('plan-feedback').value;
    
    try {
        addLog('正在提交反馈...');
        
        // Optimize UX: If modifying, set flag immediately to prevent old UI flash
        if (!isApproved) {
            isRegeneratingPlan = true;
            const planSection = document.getElementById('plan-section');
            if (planSection) {
                 // Hide notice and actions immediately
                const noticeEl = planSection.querySelector('.notice');
                const actionsEl = planSection.querySelector('.actions');
                if (noticeEl) noticeEl.classList.add('hidden');
                if (actionsEl) actionsEl.classList.add('hidden');
            }

            // Clear current plan display immediately and show loading
            const planContentDiv = document.getElementById('plan-content');
            if (planContentDiv) {
                planContentDiv.innerHTML = '<div class="alert alert-info">🔄 正在根据您的反馈重新生成计划，请稍候...</div>';
            }
            // Hide visualize section immediately via DOM (will be reinforced by handleStateLogic)
            document.getElementById('visualization-section').classList.add('hidden');
            
            // Hide feedback input area
             document.getElementById('feedback-input').classList.add('hidden');
        }

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
            // Logic handled by isRegeneratingPlan and handleStateLogic now
            if (isApproved) {
                document.getElementById('plan-section').classList.add('hidden');
            }
            // Reset status tracking so polling updates state
            previousStatus = null;
        } else {
            addLog('反馈提交失败', 'error');
            isRegeneratingPlan = false; // Revert if failed
        }
    } catch (e) {
        console.error(e);
        addLog('反馈提交错误', 'error');
        isRegeneratingPlan = false; // Revert if failed
    }
}

function updateMindMap(state) {
    const container = document.getElementById('mind-map-container');
    if (!state.research_plan || !state.research_plan.steps) return;

    let html = `<div class="tree-root"><span class="node-root">🎯 ${state.research_plan.objective || 'Research Goal'}</span>`;
    html += '<ul class="tree-branch" style="list-style: none; padding-left: 0;">';
    
    state.research_plan.steps.forEach((step, index) => {
        const isCurrent = (index === state.current_step_index);
        let statusIcon = '⏳';
        if (step.status === 'completed') statusIcon = '✅';
        else if (step.status === 'failed') statusIcon = '❌';
        else if (isCurrent) statusIcon = '🔄';

        const activeClass = isCurrent ? 'node-active' : '';
        const depth = step.depth || 1;
        const indent = (depth - 1) * 20;
        
        html += `<li class="tree-item" style="margin-left: ${indent}px; border-left: ${depth > 1 ? '1px dashed #ccc' : 'none'};">
            <div class="node-step ${activeClass}" style="padding: 5px; margin-bottom: 5px; border: 1px solid #eee; border-radius: 4px;">
                <div style="display: flex; align-items: center;">
                    <span class="step-status" style="margin-right: 5px;">${statusIcon}</span>
                    <span class="step-title" style="font-weight: bold;">${step.title}</span>
                    <span class="badge" style="font-size: 0.7em; margin-left: auto; background: #f0f0f0;">Depth ${depth}</span>
                </div>
                ${step.description ? `<div class="step-desc" style="font-size: 0.9em; color: #666; margin-left: 20px;">${step.description}</div>` : ''}
                ${step.assigned_agent ? `<div class="step-agent" style="font-size: 0.8em; color: #888; margin-left: 20px;">🤖 ${step.assigned_agent}</div>` : ''}
                ${step.status === 'failed' && step.error_message ? `<div class="step-error" style="font-size: 0.8em; color: #dc2626; margin-top: 5px; margin-left: 20px; background: #fee2e2; padding: 4px; border-radius: 4px;">⚠️ ${step.error_message}</div>` : ''}
            </div>
        </li>`;
    });
    
    html += '</ul></div>';
    container.innerHTML = html;
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
    const clone = originalElement.cloneNode(true);
    const container = document.createElement('div');
    container.style.position = 'fixed';
    container.style.left = '-10000px';
    container.style.top = '0';
    container.style.width = '800px';
    container.style.backgroundColor = 'white';
    container.style.zIndex = '-9999';
    clone.classList.add('pdf-export-mode');
    clone.style.width = '100%';
    clone.style.height = 'auto';
    clone.style.overflow = 'visible';
    clone.style.maxHeight = 'none';

    const paddingDiv = document.createElement('div');
    paddingDiv.style.height = '50px';
    paddingDiv.style.clear = 'both';
    clone.appendChild(paddingDiv);
    container.appendChild(clone);
    document.body.appendChild(container);

    setTimeout(() => {
        const opt = {
            margin:       [10, 10, 10, 10], 
            filename:     `Research_Report_${currentThreadId || 'doc'}.pdf`,
            image:        { type: 'jpeg', quality: 0.98 },
            html2canvas:  { scale: 2, useCORS: true, letterRendering: true, width: 800, windowWidth: 800, scrollY: 0, x: 0, y: 0 },
            jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' },
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
            alert('PDF 生成库未加载');
            document.body.removeChild(container);
        }
    }, 100);
}
