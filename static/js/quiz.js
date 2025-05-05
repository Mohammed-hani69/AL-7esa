// Quiz functionality

// Initialize quiz
document.addEventListener('DOMContentLoaded', function() {
  initQuizTimer();
  setupQuizForm();
  
  // Initialize quiz question handling
  if (document.getElementById('add-question-form')) {
    document.getElementById('question-type').addEventListener('change', addQuizQuestion);
    addQuizQuestion(); // Call once to setup initial state
  }
  
  // Highlight selected options
  const quizOptions = document.querySelectorAll('.quiz-option');
  quizOptions.forEach(option => {
    option.addEventListener('click', function() {
      // Remove selected class from all options in the same question
      const questionOptions = this.closest('.quiz-options').querySelectorAll('.quiz-option');
      questionOptions.forEach(opt => opt.classList.remove('selected'));
      
      // Add selected class to clicked option
      this.classList.add('selected');
      
      // Set the radio button as checked
      const radio = this.querySelector('input[type="radio"]');
      if (radio) {
        radio.checked = true;
      }
    });
  });

  // Initialize question type handling
  const questionType = document.getElementById('question-type');
  if (questionType) {
    questionType.addEventListener('change', handleQuestionTypeChange);
    handleQuestionTypeChange(); // Initial setup
  }
});

// Initialize quiz timer
function initQuizTimer() {
  const timerElement = document.getElementById('quiz-timer');
  const quizForm = document.getElementById('quiz-form');
  
  if (timerElement && quizForm) {
    const duration = parseInt(timerElement.getAttribute('data-duration') || '0');
    const startTime = parseInt(timerElement.getAttribute('data-start-time') || Date.now());
    
    if (duration > 0) {
      // Calculate end time
      const endTime = startTime + (duration * 60 * 1000);
      
      // Update timer every second
      const timerInterval = setInterval(function() {
        const now = Date.now();
        const timeLeft = Math.max(0, endTime - now);
        
        // If time is up, submit the quiz
        if (timeLeft <= 0) {
          clearInterval(timerInterval);
          timerElement.textContent = 'انتهى الوقت!';
          
          // Auto-submit the quiz
          alert('انتهى وقت الاختبار! سيتم تسليم إجاباتك الآن.');
          quizForm.submit();
          return;
        }
        
        // Format and display remaining time
        const minutes = Math.floor(timeLeft / (60 * 1000));
        const seconds = Math.floor((timeLeft % (60 * 1000)) / 1000);
        
        timerElement.textContent = `الوقت المتبقي: ${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
      }, 1000);
    }
  }
}

// Setup quiz form
function setupQuizForm() {
  const quizForm = document.getElementById('quiz-form');
  
  if (quizForm) {
    quizForm.addEventListener('submit', function(e) {
      // Check if any required questions are unanswered
      const requiredQuestions = document.querySelectorAll('.quiz-question[data-required="true"]');
      let allAnswered = true;
      
      requiredQuestions.forEach(question => {
        const questionType = question.getAttribute('data-type');
        const questionId = question.getAttribute('data-id');
        
        if (questionType === 'multiple_choice' || questionType === 'true_false') {
          // Check if any option is selected
          const selectedOption = question.querySelector(`input[name="question_${questionId}"]:checked`);
          
          if (!selectedOption) {
            allAnswered = false;
            question.classList.add('border-danger');
          } else {
            question.classList.remove('border-danger');
          }
        } else if (questionType === 'short_answer' || questionType === 'essay') {
          // Check if text is entered
          const textAnswer = question.querySelector(`textarea[name="question_${questionId}"]`).value.trim();
          
          if (!textAnswer) {
            allAnswered = false;
            question.classList.add('border-danger');
          } else {
            question.classList.remove('border-danger');
          }
        }
      });
      
      if (!allAnswered) {
        e.preventDefault();
        alert('يرجى الإجابة على جميع الأسئلة المطلوبة قبل التسليم.');
        window.scrollTo(0, 0);
      } else {
        // Confirm submission
        if (!confirm('هل أنت متأكد من تسليم الاختبار؟ لا يمكنك تعديل إجاباتك بعد التسليم.')) {
          e.preventDefault();
        }
      }
    });
  }
}

// Add new question to a quiz
function addNewQuestion() {
  const form = document.getElementById('add-question-form');
  
  // Validate the form
  const questionText = form.querySelector('#question-text').value.trim();
  const questionType = form.querySelector('#question-type').value;
  
  if (!questionText) {
    showAlert('يرجى إدخال نص السؤال', 'danger');
    return;
  }
  
  if (questionType === 'multiple_choice') {
    // Ensure we have at least two options
    const options = form.querySelectorAll('input[name="option_text[]"]');
    if (options.length < 2) {
      showAlert('يجب إضافة خيارين على الأقل', 'danger');
      return;
    }
    
    // Ensure an option is selected as correct
    const correctOption = form.querySelector('input[name="correct_option"]:checked');
    if (!correctOption) {
      showAlert('يرجى تحديد الخيار الصحيح', 'danger');
      return;
    }
    
    // Ensure all options have text
    let allOptionsHaveText = true;
    options.forEach(option => {
      if (!option.value.trim()) {
        allOptionsHaveText = false;
      }
    });
    
    if (!allOptionsHaveText) {
      showAlert('يرجى إدخال نص لجميع الخيارات', 'danger');
      return;
    }
  }
  
  // Submit the form
  form.submit();
}

// Delete a question
function deleteQuestion(questionId, questionText) {
  if (confirm(`هل أنت متأكد من حذف السؤال: "${questionText}"؟`)) {
    document.getElementById(`delete-question-${questionId}`).submit();
  }
}

// Show quiz results
function showQuizResults() {
  const resultElements = document.querySelectorAll('.result-details');
  
  resultElements.forEach(element => {
    element.classList.toggle('d-none');
  });
  
  const toggleButton = document.getElementById('toggle-results-btn');
  if (toggleButton) {
    if (toggleButton.textContent.includes('عرض')) {
      toggleButton.textContent = 'إخفاء التفاصيل';
    } else {
      toggleButton.textContent = 'عرض التفاصيل';
    }
  }
}

// Highlight answered questions
function highlightAnsweredQuestions() {
  // Mark multiple choice questions as answered when an option is selected
  const multipleChoiceInputs = document.querySelectorAll('input[type="radio"][name^="question_"]');
  
  multipleChoiceInputs.forEach(input => {
    input.addEventListener('change', function() {
      const questionId = this.name.split('_')[1];
      const questionElement = document.getElementById(`question-${questionId}`);
      
      if (questionElement) {
        questionElement.classList.add('answered');
        updateProgressBar();
      }
    });
  });
  
  // Mark text questions as answered when text is entered
  const textInputs = document.querySelectorAll('textarea[name^="question_"]');
  
  textInputs.forEach(input => {
    input.addEventListener('input', function() {
      const questionId = this.name.split('_')[1];
      const questionElement = document.getElementById(`question-${questionId}`);
      
      if (questionElement) {
        if (this.value.trim().length > 0) {
          questionElement.classList.add('answered');
        } else {
          questionElement.classList.remove('answered');
        }
        
        updateProgressBar();
      }
    });
  });
  
  // Initial update
  updateProgressBar();
}

// Update progress bar
function updateProgressBar() {
  const totalQuestions = document.querySelectorAll('.quiz-question').length;
  const answeredQuestions = document.querySelectorAll('.quiz-question.answered').length;
  
  const progressBar = document.getElementById('quiz-progress');
  if (progressBar && totalQuestions > 0) {
    const percentage = Math.round((answeredQuestions / totalQuestions) * 100);
    progressBar.style.width = `${percentage}%`;
    progressBar.textContent = `${percentage}%`;
    
    const progressElement = document.getElementById('quiz-progress-text');
    if (progressElement) {
      progressElement.textContent = `${answeredQuestions} من ${totalQuestions}`;
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
                ${optionIndex > 1 ? `
                    <button type="button" class="btn btn-sm btn-danger" onclick="removeQuizOption(this)">
                        <i class="fas fa-times"></i>
                    </button>
                ` : ''}
            </div>
        `;
        
        optionsContainer.appendChild(optionDiv);
    }
}

// Remove quiz option
function removeQuizOption(button) {
    const optionsContainer = document.getElementById('question-options-container');
    const optionDiv = button.closest('.form-row');
    
    if (optionsContainer && optionsContainer.children.length > 2) {
        optionDiv.remove();
        
        // Renumber remaining options
        const options = optionsContainer.children;
        for (let i = 0; i < options.length; i++) {
            const radio = options[i].querySelector('input[type="radio"]');
            const input = options[i].querySelector('input[type="text"]');
            
            radio.id = `option-${i}`;
            radio.value = i;
            if (!input.readOnly) {
                input.placeholder = `الخيار ${i + 1}`;
            }
        }
    }
}

// Handle question type change
function handleQuestionTypeChange() {
    const questionType = document.getElementById('question-type');
    const optionsContainer = document.getElementById('question-options-container');
    const optionsControls = document.getElementById('options-controls');
    
    if (questionType && optionsContainer && optionsControls) {
        const type = questionType.value;
        
        // Clear existing options
        optionsContainer.innerHTML = '';
        
        if (type === 'multiple_choice' || type === 'true_false') {
            optionsControls.classList.remove('d-none');
            
            if (type === 'true_false') {
                // Add true/false options
                addTrueFalseOptions();
                optionsControls.classList.add('d-none');
            } else {
                // Add initial options for multiple choice
                addQuizOption();
                addQuizOption();
            }
        } else {
            optionsControls.classList.add('d-none');
        }
    }
}

// Add true/false options
function addTrueFalseOptions() {
    const optionsContainer = document.getElementById('question-options-container');
    
    if (optionsContainer) {
        optionsContainer.innerHTML = `
            <div class="form-row mb-2">
                <div class="col-1">
                    <input class="form-check-input" type="radio" name="correct_option" id="option-0" value="0" checked>
                </div>
                <div class="col-10">
                    <input type="text" class="form-control" name="option_text[]" value="صح" readonly>
                </div>
            </div>
            <div class="form-row mb-2">
                <div class="col-1">
                    <input class="form-check-input" type="radio" name="correct_option" id="option-1" value="1">
                </div>
                <div class="col-10">
                    <input type="text" class="form-control" name="option_text[]" value="خطأ" readonly>
                </div>
            </div>
        `;
    }
}

// Validate add question form
document.addEventListener('DOMContentLoaded', function() {
    const addQuestionForm = document.getElementById('add-question-form');
    
    if (addQuestionForm) {
        addQuestionForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const questionText = document.getElementById('question-text').value.trim();
            const questionType = document.getElementById('question-type').value;
            
            if (!questionText) {
                alert('يرجى إدخال نص السؤال');
                return;
            }
            
            if (questionType === 'multiple_choice') {
                // Check if at least two options exist
                const options = document.querySelectorAll('input[name="option_text[]"]');
                if (options.length < 2) {
                    alert('يجب إضافة خيارين على الأقل');
                    return;
                }
                
                // Check if all options have text
                let allOptionsValid = true;
                options.forEach(option => {
                    if (!option.value.trim()) {
                        allOptionsValid = false;
                    }
                });
                
                if (!allOptionsValid) {
                    alert('يرجى إدخال نص لجميع الخيارات');
                    return;
                }
                
                // Check if a correct answer is selected
                const correctOption = document.querySelector('input[name="correct_option"]:checked');
                if (!correctOption) {
                    alert('يرجى تحديد الإجابة الصحيحة');
                    return;
                }
            }
            
            this.submit();
        });
    }
});
