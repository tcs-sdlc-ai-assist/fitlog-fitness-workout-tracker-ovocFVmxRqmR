# Changelog

All notable changes to the FitLog Workout Tracker project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-01-15

### Added

#### User Authentication
- User registration with email and password
- Secure login and logout with JWT-based authentication
- Password hashing with bcrypt for secure credential storage
- Token refresh mechanism for seamless session management
- Password reset functionality via email
- User profile management with editable personal details

#### Exercise Library
- Comprehensive built-in exercise database with common exercises
- Exercises categorized by muscle group (chest, back, shoulders, arms, legs, core, cardio)
- Exercise details including description, instructions, and target muscles
- Support for custom user-created exercises
- Exercise search and filtering by name, category, and muscle group
- Equipment type tagging (barbell, dumbbell, machine, bodyweight, cable, kettlebell)

#### Workout Logging
- Create and log individual workout sessions
- Add multiple exercises to a single workout
- Track sets, reps, weight, duration, and distance per exercise
- Rest timer tracking between sets
- Workout notes and session-level comments
- Edit and delete past workout entries
- Workout duration tracking with start and end timestamps

#### Workout Templates
- Create reusable workout templates from scratch
- Save existing workouts as templates for future use
- Organize templates by workout type (push, pull, legs, upper, lower, full body)
- Quick-start workouts from saved templates
- Edit and manage template library
- Share templates between users

#### Body Measurements
- Log body weight over time
- Track body measurements (chest, waist, hips, arms, thighs, calves, neck)
- Body fat percentage tracking
- BMI automatic calculation
- Measurement history with date-stamped entries
- Support for metric and imperial unit systems

#### Progress Tracking
- Personal records (PRs) detection and tracking per exercise
- Strength progression charts for individual exercises
- Volume tracking (total sets, reps, and tonnage per session)
- Workout frequency and consistency analytics
- Historical comparison of performance over custom date ranges
- Streak tracking for consecutive workout days

#### Dashboard
- At-a-glance summary of recent workout activity
- Weekly and monthly workout frequency overview
- Current body weight and measurement trends
- Recent personal records display
- Upcoming scheduled workouts
- Quick-action buttons for starting a new workout or logging measurements

#### Admin Management
- Admin panel for user account management
- Ability to manage the global exercise library
- User activity monitoring and usage statistics
- System-wide configuration settings
- Role-based access control (admin, standard user)
- Bulk operations for exercise and user management

#### Mobile-First UI
- Responsive design optimized for mobile devices
- Touch-friendly interface elements for gym use
- Tailwind CSS utility-first styling throughout
- Accessible navigation with collapsible sidebar
- Dark mode support for low-light gym environments
- Fast-loading pages with optimized asset delivery
- Progressive enhancement for desktop and tablet viewports

### Technical Foundation
- Python FastAPI backend with async request handling
- SQLAlchemy 2.0 async ORM with SQLite/PostgreSQL support
- Pydantic v2 schemas for request/response validation
- JWT authentication with secure token management
- RESTful API design with versioned endpoints
- Comprehensive error handling with proper HTTP status codes
- Structured logging throughout the application
- CORS configuration for frontend integration
- Database migrations support
- Automated test suite with pytest and httpx