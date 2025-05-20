// Base modal class with common functionality
class BaseModal {
    constructor() {
        this.modal = null;
        this.form = null;
    }

    createModalContainer(title, formId) {
        this.modal = document.createElement('div');
        this.modal.className = 'modal';
        this.modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>${title}</h2>
                    <span class="close">&times;</span>
                </div>
                <div class="modal-body">
                    <form id="${formId}">
                        <div class="form-group">
                            <label>Position (mm)</label>
                            <div class="input-group">
                                <div>
                                    <label>X Min:</label>
                                    <input type="number" step="0.1" name="xMin" required>
                                </div>
                                <div>
                                    <label>X Max:</label>
                                    <input type="number" step="0.1" name="xMax" required>
                                </div>
                            </div>
                        </div>
                        <div class="form-group">
                            <label>Width (mm)</label>
                            <input type="number" step="0.1" name="width" required>
                        </div>
                        <div class="form-group">
                            <label>Tolerances (mm)</label>
                            <div class="input-group">
                                <div>
                                    <label>Position:</label>
                                    <input type="number" step="0.1" name="positionTolerance" value="0.5" required>
                                </div>
                                <div>
                                    <label>Width:</label>
                                    <input type="number" step="0.1" name="widthTolerance" value="0.3" required>
                                </div>
                                <div>
                                    <label>Depth:</label>
                                    <input type="number" step="0.1" name="depthTolerance" value="0.2" required>
                                </div>
                            </div>
                        </div>
                        <div class="form-group">
                            <label>Expected Depth (mm)</label>
                            <input type="number" step="0.1" name="expectedDepth" value="-1.0" required>
                        </div>
                        <div class="modal-footer">
                            <button type="submit" class="btn btn-primary">Save</button>
                            <button type="button" class="btn btn-secondary cancel-btn">Cancel</button>
                        </div>
                    </form>
                </div>
            </div>
        `;

        document.body.appendChild(this.modal);
        this.form = this.modal.querySelector(`#${formId}`);
    }

    setupBaseEventListeners() {
        const closeBtn = this.modal.querySelector('.close');
        const cancelBtn = this.modal.querySelector('.cancel-btn');
        
        closeBtn.onclick = () => this.close();
        cancelBtn.onclick = () => this.close();

        window.onclick = (e) => {
            if (e.target === this.modal) {
                this.close();
            }
        };
    }

    close() {
        if (this.modal) {
            this.modal.remove();
            this.modal = null;
            this.form = null;
        }
    }

    getFormData() {
        return {
            x_min: parseFloat(this.form.xMin.value),
            x_max: parseFloat(this.form.xMax.value),
            width: parseFloat(this.form.width.value),
            position_tolerance: parseFloat(this.form.positionTolerance.value),
            width_tolerance: parseFloat(this.form.widthTolerance.value),
            depth_tolerance: parseFloat(this.form.depthTolerance.value),
            expected_depth: parseFloat(this.form.expectedDepth.value)
        };
    }
}

// Add Feature Modal
class AddFeatureModal extends BaseModal {
    constructor() {
        super();
        this.onSaveCallback = null;
    }

    show(onSave) {
        // Close any existing modal first
        this.close();
        this.onSaveCallback = onSave;
        this.createModalContainer('Add New Feature', 'addFeatureForm');
        this.resetFormFields(); // Ensure fields are blank/default
        this.setupEventListeners();
    }

    resetFormFields() {
        this.form.xMin.value = '';
        this.form.xMax.value = '';
        this.form.width.value = '';
        this.form.positionTolerance.value = '0.5';
        this.form.widthTolerance.value = '0.3';
        this.form.depthTolerance.value = '0.2';
        this.form.expectedDepth.value = '-1.0';
    }

    setupEventListeners() {
        super.setupBaseEventListeners();
        
        this.form.onsubmit = (e) => {
            e.preventDefault();
            try {
                const formData = this.getFormData();
                if (this.onSaveCallback) {
                    this.onSaveCallback(formData);
                }
                this.close();
            } catch (error) {
                alert('Please enter valid numeric values');
            }
        };
    }
}

// Edit Feature Modal
class EditFeatureModal extends BaseModal {
    constructor() {
        super();
        this.onSaveCallback = null;
        this.featureId = null;
    }

    show(featureData, onSave) {
        // Close any existing modal first
        this.close();
        
        this.onSaveCallback = onSave;
        this.featureId = featureData.id;
        this.createModalContainer('Edit Feature', 'editFeatureForm');
        this.populateForm(featureData);
        this.setupEventListeners();
    }

    populateForm(featureData) {
        this.form.xMin.value = featureData.x_min;
        this.form.xMax.value = featureData.x_max;
        this.form.width.value = featureData.width;
        this.form.positionTolerance.value = featureData.position_tolerance;
        this.form.widthTolerance.value = featureData.width_tolerance;
        this.form.depthTolerance.value = featureData.depth_tolerance;
        this.form.expectedDepth.value = featureData.expected_depth;
    }

    setupEventListeners() {
        super.setupBaseEventListeners();
        
        this.form.onsubmit = (e) => {
            e.preventDefault();
            try {
                const formData = this.getFormData();
                formData.id = this.featureId; // Include the feature ID for updates
                if (this.onSaveCallback) {
                    this.onSaveCallback(formData);
                }
                this.close();
            } catch (error) {
                alert('Please enter valid numeric values');
            }
        };
    }
}

// Create global instances
const addFeatureModal = new AddFeatureModal();
const editFeatureModal = new EditFeatureModal(); 