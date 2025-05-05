
CREATE TABLE [User] (
    id INT PRIMARY KEY IDENTITY,
    name NVARCHAR(100) NOT NULL,
    phone NVARCHAR(20) UNIQUE NOT NULL,
    alt_phone NVARCHAR(20),
    email NVARCHAR(100) UNIQUE,
    password_hash NVARCHAR(256),
    role NVARCHAR(20) NOT NULL,
    profile_picture NVARCHAR(255),
    address NVARCHAR(255),
    interests TEXT,
    created_at DATETIME DEFAULT GETDATE(),
    updated_at DATETIME DEFAULT GETDATE(),
    is_active BIT DEFAULT 1,
    firebase_uid NVARCHAR(100) UNIQUE
);

CREATE TABLE SubscriptionPlan (
    id INT PRIMARY KEY IDENTITY,
    name NVARCHAR(100) NOT NULL,
    description TEXT,
    price FLOAT NOT NULL,
    duration_days INT NOT NULL,
    max_classrooms INT NOT NULL,
    has_chat BIT DEFAULT 0,
    allow_assistant BIT DEFAULT 0,
    advanced_analytics BIT DEFAULT 0,
    created_at DATETIME DEFAULT GETDATE(),
    updated_at DATETIME DEFAULT GETDATE()
);

CREATE TABLE Subscription (
    id INT PRIMARY KEY IDENTITY,
    user_id INT NOT NULL,
    plan_id INT NOT NULL,
    start_date DATETIME DEFAULT GETDATE(),
    end_date DATETIME NOT NULL,
    is_active BIT DEFAULT 1,
    is_trial BIT DEFAULT 0,
    created_at DATETIME DEFAULT GETDATE(),
    updated_at DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (user_id) REFERENCES [User](id),
    FOREIGN KEY (plan_id) REFERENCES SubscriptionPlan(id)
);

CREATE TABLE Classroom (
    id INT PRIMARY KEY IDENTITY,
    code NVARCHAR(10) UNIQUE NOT NULL,
    name NVARCHAR(100) NOT NULL,
    description TEXT,
    subject NVARCHAR(100) NOT NULL,
    grade NVARCHAR(50) NOT NULL,
    academic_year NVARCHAR(20) NOT NULL,
    color NVARCHAR(20),
    image NVARCHAR(255),
    is_free BIT DEFAULT 1,
    price FLOAT,
    duration_days INT,
    teacher_id INT NOT NULL,
    assistant_id INT,
    created_at DATETIME DEFAULT GETDATE(),
    updated_at DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (teacher_id) REFERENCES [User](id),
    FOREIGN KEY (assistant_id) REFERENCES [User](id)
);

CREATE TABLE ClassroomEnrollment (
    id INT PRIMARY KEY IDENTITY,
    user_id INT NOT NULL,
    classroom_id INT NOT NULL,
    joined_at DATETIME DEFAULT GETDATE(),
    is_active BIT DEFAULT 1,
    points INT DEFAULT 0,
    payment_status NVARCHAR(20),
    payment_date DATETIME,
    CONSTRAINT unique_enrollment UNIQUE (user_id, classroom_id),
    FOREIGN KEY (user_id) REFERENCES [User](id),
    FOREIGN KEY (classroom_id) REFERENCES Classroom(id)
);

CREATE TABLE ClassroomContent (
    id INT PRIMARY KEY IDENTITY,
    classroom_id INT NOT NULL,
    title NVARCHAR(100) NOT NULL,
    description TEXT,
    content_type NVARCHAR(20) NOT NULL,
    content_url NVARCHAR(255),
    content_text TEXT,
    created_at DATETIME DEFAULT GETDATE(),
    updated_at DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (classroom_id) REFERENCES Classroom(id)
);

CREATE TABLE Assignment (
    id INT PRIMARY KEY IDENTITY,
    classroom_id INT NOT NULL,
    title NVARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    due_date DATETIME,
    points INT DEFAULT 0,
    created_at DATETIME DEFAULT GETDATE(),
    updated_at DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (classroom_id) REFERENCES Classroom(id)
);

CREATE TABLE AssignmentSubmission (
    id INT PRIMARY KEY IDENTITY,
    enrollment_id INT NOT NULL,
    assignment_id INT NOT NULL,
    content TEXT NOT NULL,
    attachment_url NVARCHAR(255),
    submission_date DATETIME DEFAULT GETDATE(),
    grade INT,
    feedback TEXT,
    FOREIGN KEY (enrollment_id) REFERENCES ClassroomEnrollment(id),
    FOREIGN KEY (assignment_id) REFERENCES Assignment(id)
);

CREATE TABLE Quiz (
    id INT PRIMARY KEY IDENTITY,
    classroom_id INT NOT NULL,
    title NVARCHAR(100) NOT NULL,
    description TEXT,
    duration_minutes INT,
    start_time DATETIME,
    end_time DATETIME,
    is_active BIT DEFAULT 1,
    total_points INT DEFAULT 0,
    created_at DATETIME DEFAULT GETDATE(),
    updated_at DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (classroom_id) REFERENCES Classroom(id)
);

CREATE TABLE QuizQuestion (
    id INT PRIMARY KEY IDENTITY,
    quiz_id INT NOT NULL,
    question_text TEXT NOT NULL,
    question_type NVARCHAR(20) NOT NULL,
    points INT DEFAULT 1,
    position INT DEFAULT 0,
    FOREIGN KEY (quiz_id) REFERENCES Quiz(id)
);

CREATE TABLE QuizQuestionOption (
    id INT PRIMARY KEY IDENTITY,
    question_id INT NOT NULL,
    option_text TEXT NOT NULL,
    is_correct BIT DEFAULT 0,
    position INT DEFAULT 0,
    FOREIGN KEY (question_id) REFERENCES QuizQuestion(id)
);

CREATE TABLE QuizAttempt (
    id INT PRIMARY KEY IDENTITY,
    enrollment_id INT NOT NULL,
    quiz_id INT NOT NULL,
    start_time DATETIME DEFAULT GETDATE(),
    end_time DATETIME,
    score INT,
    is_completed BIT DEFAULT 0,
    CONSTRAINT unique_quiz_attempt UNIQUE (enrollment_id, quiz_id),
    FOREIGN KEY (enrollment_id) REFERENCES ClassroomEnrollment(id),
    FOREIGN KEY (quiz_id) REFERENCES Quiz(id)
);

CREATE TABLE QuizAnswer (
    id INT PRIMARY KEY IDENTITY,
    attempt_id INT NOT NULL,
    question_id INT NOT NULL,
    selected_option_id INT,
    text_answer TEXT,
    is_correct BIT,
    points_earned INT,
    FOREIGN KEY (attempt_id) REFERENCES QuizAttempt(id),
    FOREIGN KEY (question_id) REFERENCES QuizQuestion(id),
    FOREIGN KEY (selected_option_id) REFERENCES QuizQuestionOption(id)
);

CREATE TABLE Notification (
    id INT PRIMARY KEY IDENTITY,
    user_id INT NOT NULL,
    title NVARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    is_read BIT DEFAULT 0,
    created_at DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (user_id) REFERENCES [User](id)
);

CREATE TABLE ChatMessage (
    id INT PRIMARY KEY IDENTITY,
    classroom_id INT NOT NULL,
    user_id INT NOT NULL,
    message TEXT NOT NULL,
    created_at DATETIME DEFAULT GETDATE(),
    is_deleted BIT DEFAULT 0,
    FOREIGN KEY (classroom_id) REFERENCES Classroom(id),
    FOREIGN KEY (user_id) REFERENCES [User](id)
);

CREATE TABLE Payment (
    id INT PRIMARY KEY IDENTITY,
    user_id INT NOT NULL,
    classroom_id INT,
    subscription_id INT,
    amount FLOAT NOT NULL,
    currency NVARCHAR(3) DEFAULT 'SAR',
    payment_method NVARCHAR(50),
    transaction_id NVARCHAR(100),
    status NVARCHAR(20) NOT NULL,
    created_at DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (user_id) REFERENCES [User](id),
    FOREIGN KEY (classroom_id) REFERENCES Classroom(id),
    FOREIGN KEY (subscription_id) REFERENCES Subscription(id)
);
