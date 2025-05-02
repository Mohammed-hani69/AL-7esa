// Classroom management functionality

// Initialize classroom page
document.addEventListener('DOMContentLoaded', function() {
  // Setup color picker for classroom
  initClassroomColorPicker();
  
  // Setup classroom code copy button
  initClassroomCodeCopy();
  
  // Setup classroom content upload
  initContentUpload();
  
  // Setup student management
  initStudentManagement();
  
  // Track active students
  trackActiveStudents();
});

// Initialize color picker for classroom creation/edit
function initClassroomColorPicker() {
  const colorOptions = document.querySelectorAll('.color-option');
  const colorInput = document.getElementById('classroom-color');
  
  if (colorOptions.length && colorInput) {
    colorOptions.forEach(option => {
      // Set initial selected color
      if (option.getAttribute('data-color') === colorInput.value) {
        option.classList.add('selected');
      }
      
      option.addEventListener('click', function() {
        // Remove selected class from all options
        colorOptions.forEach(opt => opt.classList.remove('selected'));
        
        // Add selected class to clicked option
        this.classList.add('selected');
        
        // Update hidden input value
        colorInput.value = this.getAttribute('data-color');
        
        // Update preview if exists
        const preview = document.getElementById('color-preview');
        if (preview) {
          preview.style.backgroundColor = this.getAttribute('data-color');
        }
      });
    });
  }
}

// Initialize copy button for classroom code
function initClassroomCodeCopy() {
  const codeElement = document.getElementById('classroom-code');
  const copyButton = document.getElementById('copy-code-btn');
  
  if (codeElement && copyButton) {
    copyButton.addEventListener('click', function() {
      const code = codeElement.textContent.trim();
      copyToClipboard(code, this);
    });
  }
}

// Initialize content upload functionality
function initContentUpload() {
  const contentTypeSelect = document.getElementById('content-type');
  const contentTextContainer = document.getElementById('content-text-container');
  const contentFileContainer = document.getElementById('content-file-container');
  
  if (contentTypeSelect) {
    contentTypeSelect.addEventListener('change', function() {
      const contentType = this.value;
      
      // Show/hide appropriate containers based on content type
      if (contentType === 'text') {
        contentTextContainer.classList.remove('d-none');
        contentFileContainer.classList.add('d-none');
      } else {
        contentTextContainer.classList.add('d-none');
        contentFileContainer.classList.remove('d-none');
        
        // Update file type acceptance
        const fileInput = document.getElementById('content-file');
        if (fileInput) {
          switch (contentType) {
            case 'file':
              fileInput.accept = '.pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt';
              break;
            case 'image':
              fileInput.accept = '.jpg,.jpeg,.png,.gif,.svg';
              break;
            case 'audio':
              fileInput.accept = '.mp3,.wav,.ogg';
              break;
            case 'video':
              fileInput.accept = '.mp4,.webm,.avi';
              break;
            default:
              fileInput.accept = '';
          }
        }
      }
    });
  }
}

// Initialize student management functionality
function initStudentManagement() {
  const toggleStatusButtons = document.querySelectorAll('.toggle-student-status');
  
  toggleStatusButtons.forEach(button => {
    button.addEventListener('click', function() {
      const status = this.getAttribute('data-status');
      const studentId = this.getAttribute('data-student-id');
      const studentName = this.getAttribute('data-student-name');
      
      const newStatus = status === 'active' ? 'inactive' : 'active';
      const actionText = newStatus === 'active' ? 'تفعيل' : 'تعطيل';
      
      confirmAction(`هل أنت متأكد من ${actionText} الطالب "${studentName}"؟`, () => {
        // Submit the form
        const form = this.closest('form');
        if (form) {
          form.submit();
        }
      });
    });
  });
}

// Track and display active students
function trackActiveStudents() {
  // This would typically use Firebase real-time database or WebSockets
  // For demonstration, we'll simulate activity
  const studentStatusElements = document.querySelectorAll('.student-status');
  
  if (studentStatusElements.length) {
    // Get classroom ID
    const classroomId = document.getElementById('classroom-data')?.getAttribute('data-classroom-id');
    
    if (classroomId) {
      // Initialize Firebase real-time database if available
      if (typeof firebase !== 'undefined' && firebase.database) {
        const database = firebase.database();
        const activeStudentsRef = database.ref(`classrooms/${classroomId}/active_students`);
        
        // Listen for changes in active students
        activeStudentsRef.on('value', (snapshot) => {
          const activeStudents = snapshot.val() || {};
          
          // Update status indicators
          studentStatusElements.forEach(element => {
            const studentId = element.getAttribute('data-student-id');
            
            if (activeStudents[studentId]) {
              element.classList.remove('student-inactive');
              element.classList.add('student-active');
            } else {
              element.classList.remove('student-active');
              element.classList.add('student-inactive');
            }
          });
        });
      } else {
        // Fallback: randomly update status for demonstration
        setInterval(() => {
          studentStatusElements.forEach(element => {
            const isActive = Math.random() > 0.5;
            
            if (isActive) {
              element.classList.remove('student-inactive');
              element.classList.add('student-active');
            } else {
              element.classList.remove('student-active');
              element.classList.add('student-inactive');
            }
          });
        }, 10000); // Update every 10 seconds
      }
    }
  }
}

// Join classroom functionality
function joinClassroom() {
  const codeInput = document.getElementById('classroom-code-input');
  
  if (codeInput) {
    const code = codeInput.value.trim().toUpperCase();
    
    if (!code) {
      showAlert('يرجى إدخال كود الفصل', 'danger');
      return;
    }
    
    // Submit the form
    document.getElementById('join-classroom-form').submit();
  }
}

// Handle payment for classroom
function processPayment(classroomId) {
  // In a real application, this would integrate with a payment gateway
  // For this demo, we'll simulate a successful payment
  
  // Show loading
  const payButton = document.getElementById('pay-button');
  if (payButton) {
    payButton.disabled = true;
    payButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> جاري معالجة الدفع...';
  }
  
  // Simulate payment processing
  setTimeout(() => {
    // Submit payment form
    document.getElementById('payment-form').submit();
  }, 2000);
}

// Create assignment
function setupAssignmentForm() {
  const dueDate = document.getElementById('due-date');
  
  if (dueDate) {
    // Set minimum date to today
    const today = new Date();
    const formattedDate = today.toISOString().slice(0, 16);
    dueDate.min = formattedDate;
  }
}

// Create quiz
function setupQuizForm() {
  const startTime = document.getElementById('start-time');
  const endTime = document.getElementById('end-time');
  
  if (startTime && endTime) {
    // Set minimum start time to now
    const now = new Date();
    const formattedNow = now.toISOString().slice(0, 16);
    startTime.min = formattedNow;
    
    // Update min end time when start time changes
    startTime.addEventListener('change', function() {
      if (this.value) {
        endTime.min = this.value;
      } else {
        endTime.min = formattedNow;
      }
    });
  }
}

// Add quiz question
function addQuizQuestion() {
  const questionTypeSelect = document.getElementById('question-type');
  
  if (questionTypeSelect) {
    const questionType = questionTypeSelect.value;
    const optionsContainer = document.getElementById('question-options-container');
    
    // Show/hide options based on question type
    if (questionType === 'multiple_choice' || questionType === 'true_false') {
      optionsContainer.classList.remove('d-none');
      
      // For true/false, preset options
      if (questionType === 'true_false') {
        // Clear existing options
        optionsContainer.innerHTML = `
          <div class="form-check mb-2">
            <input class="form-check-input" type="radio" name="correct_option" id="option-0" value="0" checked>
            <label class="form-check-label" for="option-0">صح</label>
            <input type="hidden" name="option_text[]" value="صح">
          </div>
          <div class="form-check mb-2">
            <input class="form-check-input" type="radio" name="correct_option" id="option-1" value="1">
            <label class="form-check-label" for="option-1">خطأ</label>
            <input type="hidden" name="option_text[]" value="خطأ">
          </div>
        `;
      } else {
        // For multiple choice, allow adding custom options
        if (optionsContainer.children.length === 0) {
          addQuizOption();
          addQuizOption();
        }
      }
    } else {
      optionsContainer.classList.add('d-none');
    }
  }
}

// Add quiz option
function addQuizOption() {
  const optionsContainer = document.getElementById('question-options-container');
  
  if (optionsContainer) {
    const optionIndex = optionsContainer.children.length;
    
    const optionDiv = document.createElement('div');
    optionDiv.className = 'form-row mb-2';
    optionDiv.innerHTML = `
      <div class="col-1">
        <input class="form-check-input" type="radio" name="correct_option" id="option-${optionIndex}" value="${optionIndex}">
      </div>
      <div class="col-10">
        <input type="text" class="form-control" name="option_text[]" placeholder="الخيار ${optionIndex + 1}" required>
      </div>
      <div class="col-1">
        <button type="button" class="btn btn-sm btn-danger" onclick="removeQuizOption(this)">
          <i class="fas fa-times"></i>
        </button>
      </div>
    `;
    
    optionsContainer.appendChild(optionDiv);
  }
}

// Remove quiz option
function removeQuizOption(button) {
  const optionDiv = button.closest('.form-row');
  const optionsContainer = document.getElementById('question-options-container');
  
  if (optionDiv && optionsContainer) {
    // Don't remove if only two options are left
    if (optionsContainer.children.length <= 2) {
      showAlert('يجب أن يكون هناك خياران على الأقل', 'warning');
      return;
    }
    
    optionDiv.remove();
    
    // Reindex options
    const options = optionsContainer.querySelectorAll('.form-row');
    options.forEach((option, index) => {
      const radio = option.querySelector('input[type="radio"]');
      radio.id = `option-${index}`;
      radio.value = index;
      
      const input = option.querySelector('input[name="option_text[]"]');
      input.placeholder = `الخيار ${index + 1}`;
    });
  }
}
