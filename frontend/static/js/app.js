/**
 * Leitor de Simulados - Frontend Application
 * Main JavaScript application for handling UI interactions
 */

// ============================================
// State Management
// ============================================
const AppState = {
    sessionId: null,
    testType: null,
    images: [],
    currentImageIndex: -1,
    models: [],
    zoom: 1,
    showDetections: true
};

// ============================================
// API Client
// ============================================
const API = {
    baseUrl: '',
    
    async createSession(testType) {
        const formData = new FormData();
        formData.append('test_type', testType);
        const response = await fetch('/api/session/create', {
            method: 'POST',
            body: formData
        });
        return response.json();
    },
    
    async getSession(sessionId) {
        const response = await fetch(`/api/session/${sessionId}`);
        return response.json();
    },
    
    async deleteSession(sessionId) {
        const response = await fetch(`/api/session/${sessionId}`, {
            method: 'DELETE'
        });
        return response.json();
    },
    
    async getModels() {
        const response = await fetch('/api/models');
        return response.json();
    },
    
    async uploadImages(sessionId, files) {
        const formData = new FormData();
        for (const file of files) {
            formData.append('files', file);
        }
        const response = await fetch(`/api/upload/${sessionId}`, {
            method: 'POST',
            body: formData
        });
        return response.json();
    },
    
    async getImages(sessionId) {
        const response = await fetch(`/api/images/${sessionId}`);
        return response.json();
    },
    
    async getImage(sessionId, imageId, withDetections = false) {
        const response = await fetch(
            `/api/image/${sessionId}/${imageId}?with_detections=${withDetections}`
        );
        return response.json();
    },
    
    async processImage(sessionId, imageId, fsModel, ssModel, fsThreshold, ssThreshold) {
        const formData = new FormData();
        formData.append('fs_model', fsModel);
        formData.append('ss_model', ssModel);
        formData.append('fs_threshold', fsThreshold);
        formData.append('ss_threshold', ssThreshold);
        
        const response = await fetch(`/api/process/${sessionId}/${imageId}`, {
            method: 'POST',
            body: formData
        });
        return response.json();
    },
    
    async processAllImages(sessionId, fsModel, ssModel, fsThreshold, ssThreshold) {
        const formData = new FormData();
        formData.append('fs_model', fsModel);
        formData.append('ss_model', ssModel);
        formData.append('fs_threshold', fsThreshold);
        formData.append('ss_threshold', ssThreshold);
        
        const response = await fetch(`/api/process-all/${sessionId}`, {
            method: 'POST',
            body: formData
        });
        return response.json();
    },
    
    async getReport(sessionId, imageId) {
        const response = await fetch(`/api/report/${sessionId}/${imageId}`);
        return response.json();
    },
    
    async getAllReports(sessionId) {
        const response = await fetch(`/api/reports/${sessionId}`);
        return response.json();
    },
    
    async updateAnswer(sessionId, imageId, questionNumber, answer) {
        const formData = new FormData();
        formData.append('question_number', questionNumber);
        formData.append('answer', answer);
        
        const response = await fetch(`/api/update-answer/${sessionId}/${imageId}`, {
            method: 'POST',
            body: formData
        });
        return response.json();
    },
    
    async exportReports(sessionId, format = 'json') {
        const response = await fetch(`/api/export/${sessionId}?format=${format}`);
        return response.json();
    }
};

// ============================================
// UI Components
// ============================================
const UI = {
    elements: {},
    
    init() {
        // Cache DOM elements
        this.elements = {
            // Session
            sessionForm: document.getElementById('sessionForm'),
            testType: document.getElementById('testType'),
            sessionStatus: document.getElementById('sessionStatus'),
            
            // Upload
            uploadPanel: document.getElementById('uploadPanel'),
            uploadArea: document.getElementById('uploadArea'),
            fileInput: document.getElementById('fileInput'),
            browseBtn: document.getElementById('browseBtn'),
            uploadProgress: document.getElementById('uploadProgress'),
            progressFill: document.getElementById('progressFill'),
            progressText: document.getElementById('progressText'),
            
            // Models
            modelPanel: document.getElementById('modelPanel'),
            fsModel: document.getElementById('fsModel'),
            ssModel: document.getElementById('ssModel'),
            fsThreshold: document.getElementById('fsThreshold'),
            ssThreshold: document.getElementById('ssThreshold'),
            fsThresholdValue: document.getElementById('fsThresholdValue'),
            ssThresholdValue: document.getElementById('ssThresholdValue'),
            processBtn: document.getElementById('processBtn'),
            processAllBtn: document.getElementById('processAllBtn'),
            
            // Export
            exportPanel: document.getElementById('exportPanel'),
            exportJsonBtn: document.getElementById('exportJsonBtn'),
            exportCsvBtn: document.getElementById('exportCsvBtn'),
            
            // Image Viewer
            canvasContainer: document.getElementById('canvasContainer'),
            placeholder: document.getElementById('placeholder'),
            canvas: document.getElementById('imageCanvas'),
            prevImageBtn: document.getElementById('prevImageBtn'),
            nextImageBtn: document.getElementById('nextImageBtn'),
            imageCounter: document.getElementById('imageCounter'),
            showDetections: document.getElementById('showDetections'),
            zoomInBtn: document.getElementById('zoomInBtn'),
            zoomOutBtn: document.getElementById('zoomOutBtn'),
            fitBtn: document.getElementById('fitBtn'),
            
            // Image List & Results
            imageList: document.getElementById('imageList'),
            imageCount: document.getElementById('imageCount'),
            resultsPanel: document.getElementById('resultsPanel'),
            cpfValue: document.getElementById('cpfValue'),
            answersGrid: document.getElementById('answersGrid'),
            
            // Overlays
            loadingOverlay: document.getElementById('loadingOverlay'),
            loadingMessage: document.getElementById('loadingMessage'),
            toastContainer: document.getElementById('toastContainer')
        };
    },
    
    showLoading(message = 'Processando...') {
        this.elements.loadingMessage.textContent = message;
        this.elements.loadingOverlay.style.display = 'flex';
    },
    
    hideLoading() {
        this.elements.loadingOverlay.style.display = 'none';
    },
    
    showToast(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        this.elements.toastContainer.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideIn 0.3s ease reverse';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },
    
    updateSessionStatus(sessionId, testType) {
        if (sessionId) {
            this.elements.sessionStatus.textContent = 
                `Sessão: ${sessionId.substring(0, 8)}... | Tipo: ${testType}`;
        } else {
            this.elements.sessionStatus.textContent = 'Nenhuma sessão ativa';
        }
    },
    
    populateModelSelects(models) {
        const fsModels = models.filter(m => m.target_stage === 'FIRST' || m.target_stage === 'BOTH');
        const ssModels = models.filter(m => m.target_stage === 'SECOND' || m.target_stage === 'BOTH');
        
        this.elements.fsModel.innerHTML = '<option value="">Selecione...</option>';
        this.elements.ssModel.innerHTML = '<option value="">Selecione...</option>';
        
        fsModels.forEach(m => {
            const option = document.createElement('option');
            option.value = m.rel_path;
            option.textContent = `${m.name} (${m.model_type})`;
            this.elements.fsModel.appendChild(option);
        });
        
        ssModels.forEach(m => {
            const option = document.createElement('option');
            option.value = m.rel_path;
            option.textContent = `${m.name} (${m.model_type})`;
            this.elements.ssModel.appendChild(option);
        });
    },
    
    updateImageList(images) {
        this.elements.imageList.innerHTML = '';
        this.elements.imageCount.textContent = `(${images.length})`;
        
        if (images.length === 0) {
            this.elements.imageList.innerHTML = '<li class="empty-message">Nenhuma imagem carregada</li>';
            return;
        }
        
        images.forEach((img, index) => {
            const li = document.createElement('li');
            li.textContent = img.filename;
            li.dataset.index = index;
            li.dataset.id = img.id;
            
            if (img.processed) li.classList.add('processed');
            if (index === AppState.currentImageIndex) li.classList.add('selected');
            
            li.addEventListener('click', () => selectImage(index));
            this.elements.imageList.appendChild(li);
        });
    },
    
    updateImageCounter() {
        const total = AppState.images.length;
        const current = AppState.currentImageIndex >= 0 ? AppState.currentImageIndex + 1 : 0;
        this.elements.imageCounter.textContent = `${current} / ${total}`;
    },
    
    async displayImage(imageData, showDetections = true) {
        const canvas = this.elements.canvas;
        const ctx = canvas.getContext('2d');
        
        const img = new Image();
        img.onload = () => {
            canvas.width = img.width;
            canvas.height = img.height;
            ctx.drawImage(img, 0, 0);
            
            canvas.style.display = 'block';
            this.elements.placeholder.style.display = 'none';
            
            this.applyZoom();
        };
        img.src = `data:image/jpeg;base64,${imageData}`;
    },
    
    clearCanvas() {
        this.elements.canvas.style.display = 'none';
        this.elements.placeholder.style.display = 'flex';
    },
    
    applyZoom() {
        const canvas = this.elements.canvas;
        canvas.style.transform = `scale(${AppState.zoom})`;
        canvas.style.transformOrigin = 'center center';
    },
    
    displayReport(report) {
        if (!report) {
            this.elements.resultsPanel.style.display = 'none';
            return;
        }
        
        this.elements.resultsPanel.style.display = 'block';
        this.elements.cpfValue.textContent = report.owner_cpf || '-';
        
        this.elements.answersGrid.innerHTML = '';
        
        const questions = report.questions || [];
        questions.forEach(q => {
            const item = document.createElement('div');
            item.className = 'answer-item' + (q.updated ? ' updated' : '');
            
            item.innerHTML = `
                <span class="q-number">${q.number}:</span>
                <select data-question="${q.number}">
                    <option value="">-</option>
                    <option value="A" ${q.answer === 'A' ? 'selected' : ''}>A</option>
                    <option value="B" ${q.answer === 'B' ? 'selected' : ''}>B</option>
                    <option value="C" ${q.answer === 'C' ? 'selected' : ''}>C</option>
                    <option value="D" ${q.answer === 'D' ? 'selected' : ''}>D</option>
                    <option value="E" ${q.answer === 'E' ? 'selected' : ''}>E</option>
                </select>
            `;
            
            const select = item.querySelector('select');
            select.addEventListener('change', (e) => updateAnswer(q.number, e.target.value));
            
            this.elements.answersGrid.appendChild(item);
        });
    },
    
    showPanels(show) {
        this.elements.uploadPanel.style.display = show ? 'block' : 'none';
        this.elements.modelPanel.style.display = show ? 'block' : 'none';
        this.elements.exportPanel.style.display = show ? 'block' : 'none';
    }
};

// ============================================
// Event Handlers
// ============================================

async function createSession(e) {
    e.preventDefault();
    
    const testType = UI.elements.testType.value;
    if (!testType) {
        UI.showToast('Selecione um tipo de prova', 'warning');
        return;
    }
    
    try {
        UI.showLoading('Criando sessão...');
        const result = await API.createSession(testType);
        
        AppState.sessionId = result.session_id;
        AppState.testType = testType;
        
        UI.updateSessionStatus(result.session_id, testType);
        UI.showPanels(true);
        
        // Load available models
        const modelsResult = await API.getModels();
        AppState.models = modelsResult.models;
        UI.populateModelSelects(AppState.models);
        
        UI.hideLoading();
        UI.showToast('Sessão criada com sucesso!', 'success');
    } catch (error) {
        UI.hideLoading();
        UI.showToast('Erro ao criar sessão: ' + error.message, 'error');
    }
}

async function handleFileUpload(files) {
    if (!AppState.sessionId || files.length === 0) return;
    
    try {
        UI.elements.uploadProgress.style.display = 'flex';
        UI.elements.progressFill.style.width = '0%';
        
        const result = await API.uploadImages(AppState.sessionId, files);
        
        UI.elements.progressFill.style.width = '100%';
        UI.elements.progressText.textContent = '100%';
        
        // Refresh image list
        await refreshImageList();
        
        setTimeout(() => {
            UI.elements.uploadProgress.style.display = 'none';
        }, 1000);
        
        UI.showToast(`${result.total} imagem(ns) carregada(s)`, 'success');
    } catch (error) {
        UI.showToast('Erro ao fazer upload: ' + error.message, 'error');
        UI.elements.uploadProgress.style.display = 'none';
    }
}

async function refreshImageList() {
    if (!AppState.sessionId) return;
    
    const result = await API.getImages(AppState.sessionId);
    AppState.images = result.images;
    UI.updateImageList(AppState.images);
    UI.updateImageCounter();
    
    // Select first image if none selected
    if (AppState.currentImageIndex < 0 && AppState.images.length > 0) {
        await selectImage(0);
    }
}

async function selectImage(index) {
    if (index < 0 || index >= AppState.images.length) return;
    
    AppState.currentImageIndex = index;
    const image = AppState.images[index];
    
    // Update UI selection
    document.querySelectorAll('.image-list li').forEach((li, i) => {
        li.classList.toggle('selected', i === index);
    });
    
    UI.updateImageCounter();
    
    // Load image
    try {
        const showDetections = UI.elements.showDetections.checked && image.processed;
        const result = await API.getImage(AppState.sessionId, image.id, showDetections);
        UI.displayImage(result.image, showDetections);
        
        // Load report if processed
        if (image.has_report) {
            const reportResult = await API.getReport(AppState.sessionId, image.id);
            UI.displayReport(reportResult.report);
        } else {
            UI.displayReport(null);
        }
    } catch (error) {
        UI.showToast('Erro ao carregar imagem', 'error');
    }
}

async function processCurrentImage() {
    if (!AppState.sessionId || AppState.currentImageIndex < 0) {
        UI.showToast('Selecione uma imagem primeiro', 'warning');
        return;
    }
    
    const fsModel = UI.elements.fsModel.value;
    const ssModel = UI.elements.ssModel.value;
    
    if (!fsModel || !ssModel) {
        UI.showToast('Selecione os modelos de detecção', 'warning');
        return;
    }
    
    const image = AppState.images[AppState.currentImageIndex];
    
    try {
        UI.showLoading('Processando imagem...');
        
        const result = await API.processImage(
            AppState.sessionId,
            image.id,
            fsModel,
            ssModel,
            parseFloat(UI.elements.fsThreshold.value),
            parseFloat(UI.elements.ssThreshold.value)
        );
        
        UI.hideLoading();
        
        if (result.status === 'success') {
            UI.showToast(`Processamento concluído! ${result.detections_count} detecções`, 'success');
            await refreshImageList();
            await selectImage(AppState.currentImageIndex);
        } else {
            UI.showToast('Erro no processamento', 'error');
        }
    } catch (error) {
        UI.hideLoading();
        UI.showToast('Erro: ' + error.message, 'error');
    }
}

async function processAllImages() {
    if (!AppState.sessionId || AppState.images.length === 0) {
        UI.showToast('Nenhuma imagem para processar', 'warning');
        return;
    }
    
    const fsModel = UI.elements.fsModel.value;
    const ssModel = UI.elements.ssModel.value;
    
    if (!fsModel || !ssModel) {
        UI.showToast('Selecione os modelos de detecção', 'warning');
        return;
    }
    
    try {
        UI.showLoading('Processando todas as imagens...');
        
        const result = await API.processAllImages(
            AppState.sessionId,
            fsModel,
            ssModel,
            parseFloat(UI.elements.fsThreshold.value),
            parseFloat(UI.elements.ssThreshold.value)
        );
        
        UI.hideLoading();
        
        const successCount = result.results.filter(r => r.status === 'success').length;
        UI.showToast(`Processamento concluído! ${successCount}/${result.results.length} imagens`, 'success');
        
        await refreshImageList();
        if (AppState.currentImageIndex >= 0) {
            await selectImage(AppState.currentImageIndex);
        }
    } catch (error) {
        UI.hideLoading();
        UI.showToast('Erro: ' + error.message, 'error');
    }
}

async function updateAnswer(questionNumber, answer) {
    if (!AppState.sessionId || AppState.currentImageIndex < 0) return;
    
    const image = AppState.images[AppState.currentImageIndex];
    
    try {
        await API.updateAnswer(AppState.sessionId, image.id, questionNumber, answer);
        UI.showToast('Resposta atualizada', 'success');
    } catch (error) {
        UI.showToast('Erro ao atualizar resposta', 'error');
    }
}

async function exportReports(format) {
    if (!AppState.sessionId) return;
    
    try {
        const result = await API.exportReports(AppState.sessionId, format);
        
        // Download the result
        let content, filename, type;
        
        if (format === 'json') {
            content = JSON.stringify(result, null, 2);
            filename = 'relatorios.json';
            type = 'application/json';
        } else if (format === 'csv') {
            content = result.csv;
            filename = 'relatorios.csv';
            type = 'text/csv';
        }
        
        const blob = new Blob([content], { type });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
        
        UI.showToast('Exportação concluída!', 'success');
    } catch (error) {
        UI.showToast('Erro na exportação', 'error');
    }
}

function navigateImage(direction) {
    const newIndex = AppState.currentImageIndex + direction;
    if (newIndex >= 0 && newIndex < AppState.images.length) {
        selectImage(newIndex);
    }
}

function adjustZoom(delta) {
    AppState.zoom = Math.max(0.25, Math.min(4, AppState.zoom + delta));
    UI.applyZoom();
}

function fitToView() {
    AppState.zoom = 1;
    UI.applyZoom();
}

// ============================================
// Initialization
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    UI.init();
    
    // Session form
    UI.elements.sessionForm.addEventListener('submit', createSession);
    
    // File upload
    UI.elements.browseBtn.addEventListener('click', () => UI.elements.fileInput.click());
    UI.elements.uploadArea.addEventListener('click', () => UI.elements.fileInput.click());
    
    UI.elements.fileInput.addEventListener('change', (e) => {
        handleFileUpload(e.target.files);
        e.target.value = ''; // Reset input
    });
    
    // Drag and drop
    UI.elements.uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        UI.elements.uploadArea.classList.add('dragover');
    });
    
    UI.elements.uploadArea.addEventListener('dragleave', () => {
        UI.elements.uploadArea.classList.remove('dragover');
    });
    
    UI.elements.uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        UI.elements.uploadArea.classList.remove('dragover');
        handleFileUpload(e.dataTransfer.files);
    });
    
    // Model threshold sliders
    UI.elements.fsThreshold.addEventListener('input', (e) => {
        UI.elements.fsThresholdValue.textContent = e.target.value;
    });
    
    UI.elements.ssThreshold.addEventListener('input', (e) => {
        UI.elements.ssThresholdValue.textContent = e.target.value;
    });
    
    // Processing buttons
    UI.elements.processBtn.addEventListener('click', processCurrentImage);
    UI.elements.processAllBtn.addEventListener('click', processAllImages);
    
    // Image navigation
    UI.elements.prevImageBtn.addEventListener('click', () => navigateImage(-1));
    UI.elements.nextImageBtn.addEventListener('click', () => navigateImage(1));
    
    // Zoom controls
    UI.elements.zoomInBtn.addEventListener('click', () => adjustZoom(0.25));
    UI.elements.zoomOutBtn.addEventListener('click', () => adjustZoom(-0.25));
    UI.elements.fitBtn.addEventListener('click', fitToView);
    
    // Show detections toggle
    UI.elements.showDetections.addEventListener('change', () => {
        if (AppState.currentImageIndex >= 0) {
            selectImage(AppState.currentImageIndex);
        }
    });
    
    // Export buttons
    UI.elements.exportJsonBtn.addEventListener('click', () => exportReports('json'));
    UI.elements.exportCsvBtn.addEventListener('click', () => exportReports('csv'));
    
    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
        
        switch (e.key) {
            case 'ArrowLeft':
                navigateImage(-1);
                break;
            case 'ArrowRight':
                navigateImage(1);
                break;
            case '+':
            case '=':
                adjustZoom(0.25);
                break;
            case '-':
                adjustZoom(-0.25);
                break;
        }
    });
});
