/**
 * Subject Dropdown with Add Custom Subject Feature
 * 
 * This script handles the subject selection dropdown that allows:
 * 1. Selecting from existing subjects
 * 2. Adding custom subjects via "Other" option
 * 3. Dynamically updating the dropdown after adding new subjects
 */

class SubjectSelector {
    constructor(selectElementId, categoryFilter = null) {
        this.selectElement = document.getElementById(selectElementId);
        this.categoryFilter = categoryFilter;
        this.customInputContainer = null;
        this.subjects = [];
        
        if (this.selectElement) {
            this.init();
        }
    }
    
    async init() {
        await this.loadSubjects();
        this.setupEventListeners();
    }
    
    async loadSubjects() {
        try {
            const response = await fetch('/questions/api/subjects/');
            const data = await response.json();
            
            if (data.success) {
                this.subjects = data.all_subjects;
                this.populateDropdown(data.subjects);
            }
        } catch (error) {
            console.error('Error loading subjects:', error);
        }
    }
    
    populateDropdown(subjectsByCategory) {
        // Clear existing options except placeholder
        this.selectElement.innerHTML = '<option value="">-- Select Subject --</option>';
        
        // Add subjects grouped by category
        for (const [category, subjects] of Object.entries(subjectsByCategory)) {
            if (this.categoryFilter && category !== this.categoryFilter) {
                continue;
            }
            
            const optgroup = document.createElement('optgroup');
            optgroup.label = category;
            
            subjects.forEach(subject => {
                const option = document.createElement('option');
                option.value = subject.name;  // Use name as value
                option.textContent = subject.code ? `${subject.code} - ${subject.name}` : subject.name;
                option.dataset.subjectId = subject.id;
                option.dataset.subjectName = subject.name;
                optgroup.appendChild(option);
            });
            
            this.selectElement.appendChild(optgroup);
        }
        
        // Add "Other" option at the end
        const otherOption = document.createElement('option');
        otherOption.value = 'other';
        otherOption.textContent = '+ Add New Subject';
        otherOption.style.fontWeight = 'bold';
        otherOption.style.color = '#667eea';
        this.selectElement.appendChild(otherOption);
    }
    
    setupEventListeners() {
        this.selectElement.addEventListener('change', (e) => {
            if (e.target.value === 'other') {
                this.showCustomInput();
            } else {
                this.hideCustomInput();
            }
        });
    }
    
    showCustomInput() {
        // Remove existing container if any
        this.hideCustomInput();
        
        // Create custom input container
        this.customInputContainer = document.createElement('div');
        this.customInputContainer.id = 'custom-subject-container';
        this.customInputContainer.style.cssText = `
            margin-top: 15px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            border: 2px solid #667eea;
        `;
        
        this.customInputContainer.innerHTML = `
            <h4 style="margin: 0 0 15px 0; color: #667eea;">
                <i class="fas fa-plus-circle"></i> Add New Subject
            </h4>
            <div style="margin-bottom: 15px;">
                <label style="display: block; margin-bottom: 5px; font-weight: 600;">Subject Name *</label>
                <input type="text" id="custom-subject-name" class="form-control" 
                       placeholder="e.g., Computer Organization and Architecture" 
                       style="padding: 10px; border: 1px solid #ddd; border-radius: 6px; width: 100%;">
            </div>
            <div style="margin-bottom: 15px;">
                <label style="display: block; margin-bottom: 5px; font-weight: 600;">Subject Code (Optional)</label>
                <input type="text" id="custom-subject-code" class="form-control" 
                       placeholder="e.g., CS304" 
                       style="padding: 10px; border: 1px solid #ddd; border-radius: 6px; width: 100%;">
            </div>
            <div style="margin-bottom: 15px;">
                <label style="display: block; margin-bottom: 5px; font-weight: 600;">Category *</label>
                <select id="custom-subject-category" class="form-control" 
                        style="padding: 10px; border: 1px solid #ddd; border-radius: 6px; width: 100%;">
                    <option value="Computer Science">Computer Science</option>
                    <option value="Mathematics">Mathematics</option>
                    <option value="Physics">Physics</option>
                    <option value="Chemistry">Chemistry</option>
                    <option value="Electronics">Electronics</option>
                    <option value="Programming">Programming</option>
                    <option value="Engineering">Engineering</option>
                    <option value="Humanities">Humanities</option>
                    <option value="Other">Other</option>
                </select>
            </div>
            <div style="display: flex; gap: 10px;">
                <button type="button" id="save-custom-subject" class="btn-primary-custom" 
                        style="flex: 1; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px; border: none; border-radius: 6px; font-weight: 600; cursor: pointer;">
                    <i class="fas fa-check"></i> Add Subject
                </button>
                <button type="button" id="cancel-custom-subject" class="btn-cancel" 
                        style="flex: 1; background: #f8f9fa; color: #666; padding: 12px; border: 1px solid #ddd; border-radius: 6px; font-weight: 600; cursor: pointer;">
                    <i class="fas fa-times"></i> Cancel
                </button>
            </div>
            <div id="custom-subject-message" style="margin-top: 10px; display: none;"></div>
        `;
        
        // Insert after the select element
        this.selectElement.parentNode.insertBefore(
            this.customInputContainer, 
            this.selectElement.nextSibling
        );
        
        // Add event listeners
        document.getElementById('save-custom-subject').addEventListener('click', () => this.saveCustomSubject());
        document.getElementById('cancel-custom-subject').addEventListener('click', () => {
            this.selectElement.value = '';
            this.hideCustomInput();
        });
        
        // Focus on name input
        document.getElementById('custom-subject-name').focus();
    }
    
    hideCustomInput() {
        if (this.customInputContainer) {
            this.customInputContainer.remove();
            this.customInputContainer = null;
        }
    }
    
    async saveCustomSubject() {
        const nameInput = document.getElementById('custom-subject-name');
        const codeInput = document.getElementById('custom-subject-code');
        const categoryInput = document.getElementById('custom-subject-category');
        const messageDiv = document.getElementById('custom-subject-message');
        
        const name = nameInput.value.trim();
        const code = codeInput.value.trim();
        const category = categoryInput.value;
        
        if (!name) {
            this.showMessage(messageDiv, 'Please enter a subject name', 'error');
            nameInput.focus();
            return;
        }
        
        try {
            const response = await fetch('/questions/api/subjects/add/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name, code, category })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showMessage(messageDiv, 'Subject added successfully!', 'success');
                
                // Reload subjects
                await this.loadSubjects();
                
                // Select the newly added subject by name
                this.selectElement.value = data.subject.name;
                
                // Hide custom input after 1 second
                setTimeout(() => {
                    this.hideCustomInput();
                }, 1000);
            } else {
                this.showMessage(messageDiv, data.error || 'Failed to add subject', 'error');
            }
        } catch (error) {
            console.error('Error saving subject:', error);
            this.showMessage(messageDiv, 'Network error. Please try again.', 'error');
        }
    }
    
    showMessage(element, message, type) {
        element.style.display = 'block';
        element.style.padding = '10px';
        element.style.borderRadius = '6px';
        element.style.marginTop = '10px';
        
        if (type === 'success') {
            element.style.background = '#d4edda';
            element.style.color = '#155724';
            element.style.border = '1px solid #c3e6cb';
            element.innerHTML = `<i class="fas fa-check-circle"></i> ${message}`;
        } else {
            element.style.background = '#f8d7da';
            element.style.color = '#721c24';
            element.style.border = '1px solid #f5c6cb';
            element.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${message}`;
        }
    }
    
    getValue() {
        const value = this.selectElement.value;
        return value === 'other' ? null : value;
    }
    
    setValue(subjectId) {
        this.selectElement.value = subjectId;
    }
}

// Auto-initialize for common subject select elements
document.addEventListener('DOMContentLoaded', function() {
    // Initialize subject selectors for common form fields
    const subjectSelects = document.querySelectorAll('select[name="subject"]');
    subjectSelects.forEach(select => {
        if (select.id) {
            new SubjectSelector(select.id);
        }
    });
});
