// FitLog Client-Side JavaScript
// Dynamic UI interactions for workout tracking

(function () {
  "use strict";

  // ============================================================
  // Hamburger Menu Toggle
  // ============================================================
  function initHamburgerMenu() {
    const menuToggle = document.getElementById("menu-toggle");
    const mobileMenu = document.getElementById("mobile-menu");
    const menuOverlay = document.getElementById("menu-overlay");

    if (!menuToggle || !mobileMenu) return;

    menuToggle.addEventListener("click", function (e) {
      e.stopPropagation();
      mobileMenu.classList.toggle("hidden");
      if (menuOverlay) {
        menuOverlay.classList.toggle("hidden");
      }
      const expanded = menuToggle.getAttribute("aria-expanded") === "true";
      menuToggle.setAttribute("aria-expanded", String(!expanded));
    });

    if (menuOverlay) {
      menuOverlay.addEventListener("click", function () {
        mobileMenu.classList.add("hidden");
        menuOverlay.classList.add("hidden");
        menuToggle.setAttribute("aria-expanded", "false");
      });
    }

    document.addEventListener("click", function (e) {
      if (
        !mobileMenu.classList.contains("hidden") &&
        !mobileMenu.contains(e.target) &&
        !menuToggle.contains(e.target)
      ) {
        mobileMenu.classList.add("hidden");
        if (menuOverlay) {
          menuOverlay.classList.add("hidden");
        }
        menuToggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  // ============================================================
  // Workout Form: Dynamic Add/Remove Exercises and Sets
  // ============================================================
  let exerciseCounter = 0;

  function initWorkoutForm() {
    const workoutForm = document.getElementById("workout-form");
    if (!workoutForm) return;

    const exercisesContainer = document.getElementById("exercises-container");
    const addExerciseBtn = document.getElementById("add-exercise-btn");

    if (!exercisesContainer || !addExerciseBtn) return;

    // Count existing exercises on page load (for edit forms)
    const existingExercises =
      exercisesContainer.querySelectorAll("[data-exercise-index]");
    exerciseCounter = existingExercises.length;

    addExerciseBtn.addEventListener("click", function () {
      addExerciseBlock(exercisesContainer);
    });

    exercisesContainer.addEventListener("click", function (e) {
      const target = e.target.closest("[data-action]");
      if (!target) return;

      const action = target.getAttribute("data-action");

      if (action === "remove-exercise") {
        removeExerciseBlock(target);
      } else if (action === "add-set") {
        const exerciseBlock = target.closest("[data-exercise-index]");
        if (exerciseBlock) {
          addSetRow(exerciseBlock);
        }
      } else if (action === "remove-set") {
        removeSetRow(target);
      }
    });

    // If no exercises exist yet, add one by default
    if (exerciseCounter === 0) {
      addExerciseBlock(exercisesContainer);
    }

    workoutForm.addEventListener("submit", function (e) {
      if (!validateWorkoutForm(workoutForm)) {
        e.preventDefault();
      }
    });
  }

  function addExerciseBlock(container) {
    const index = exerciseCounter;
    exerciseCounter++;

    const exerciseBlock = document.createElement("div");
    exerciseBlock.setAttribute("data-exercise-index", index);
    exerciseBlock.className =
      "bg-white border border-gray-200 rounded-lg p-4 mb-4 shadow-sm";

    const exerciseSelectOptions = getExerciseOptions();

    exerciseBlock.innerHTML =
      '<div class="flex items-center justify-between mb-3">' +
      '<h4 class="text-sm font-semibold text-gray-700">Exercise #' +
      (index + 1) +
      "</h4>" +
      '<button type="button" data-action="remove-exercise" class="text-red-500 hover:text-red-700 text-sm font-medium focus:outline-none" aria-label="Remove exercise">' +
      '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>' +
      "</button>" +
      "</div>" +
      '<div class="mb-3">' +
      '<label class="block text-xs font-medium text-gray-600 mb-1">Exercise</label>' +
      '<select name="exercises[' +
      index +
      '][exercise_id]" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500" required>' +
      '<option value="">Select an exercise</option>' +
      exerciseSelectOptions +
      "</select>" +
      "</div>" +
      '<div class="sets-container" data-sets-for="' +
      index +
      '">' +
      '<div class="flex items-center justify-between mb-2">' +
      '<span class="text-xs font-medium text-gray-600">Sets</span>' +
      '<div class="grid grid-cols-3 gap-2 text-xs text-gray-500 text-center" style="width: 280px;">' +
      "<span>Weight</span>" +
      "<span>Reps</span>" +
      "<span></span>" +
      "</div>" +
      "</div>" +
      "</div>" +
      '<button type="button" data-action="add-set" class="mt-2 text-sm text-blue-600 hover:text-blue-800 font-medium focus:outline-none">' +
      "+ Add Set" +
      "</button>";

    container.appendChild(exerciseBlock);

    // Add one default set
    addSetRow(exerciseBlock);

    updateExerciseNumbers(container);
  }

  function removeExerciseBlock(button) {
    const exerciseBlock = button.closest("[data-exercise-index]");
    if (!exerciseBlock) return;

    const container = exerciseBlock.parentElement;
    const exerciseBlocks = container.querySelectorAll("[data-exercise-index]");

    if (exerciseBlocks.length <= 1) {
      showToast("At least one exercise is required.", "error");
      return;
    }

    exerciseBlock.remove();
    updateExerciseNumbers(container);
    reindexExercises(container);
  }

  function addSetRow(exerciseBlock) {
    const exerciseIndex = exerciseBlock.getAttribute("data-exercise-index");
    const setsContainer = exerciseBlock.querySelector(".sets-container");
    if (!setsContainer) return;

    const setRows = setsContainer.querySelectorAll("[data-set-index]");
    const setIndex = setRows.length;

    const setRow = document.createElement("div");
    setRow.setAttribute("data-set-index", setIndex);
    setRow.className = "flex items-center gap-2 mb-2";

    setRow.innerHTML =
      '<span class="text-xs text-gray-500 w-6 text-center flex-shrink-0">' +
      (setIndex + 1) +
      "</span>" +
      '<div class="grid grid-cols-3 gap-2" style="width: 280px;">' +
      '<input type="number" name="exercises[' +
      exerciseIndex +
      "][sets][" +
      setIndex +
      '][weight]" placeholder="lbs" min="0" step="0.5" class="border border-gray-300 rounded-md px-2 py-1.5 text-sm text-center focus:ring-2 focus:ring-blue-500 focus:border-blue-500" required>' +
      '<input type="number" name="exercises[' +
      exerciseIndex +
      "][sets][" +
      setIndex +
      '][reps]" placeholder="reps" min="1" step="1" class="border border-gray-300 rounded-md px-2 py-1.5 text-sm text-center focus:ring-2 focus:ring-blue-500 focus:border-blue-500" required>' +
      '<button type="button" data-action="remove-set" class="text-red-400 hover:text-red-600 focus:outline-none flex items-center justify-center" aria-label="Remove set">' +
      '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>' +
      "</button>" +
      "</div>";

    setsContainer.appendChild(setRow);
    updateSetNumbers(setsContainer);
  }

  function removeSetRow(button) {
    const setRow = button.closest("[data-set-index]");
    if (!setRow) return;

    const setsContainer = setRow.parentElement;
    const setRows = setsContainer.querySelectorAll("[data-set-index]");

    if (setRows.length <= 1) {
      showToast("At least one set is required.", "error");
      return;
    }

    setRow.remove();
    updateSetNumbers(setsContainer);
    reindexSets(setsContainer);
  }

  function updateExerciseNumbers(container) {
    const blocks = container.querySelectorAll("[data-exercise-index]");
    blocks.forEach(function (block, i) {
      const header = block.querySelector("h4");
      if (header) {
        header.textContent = "Exercise #" + (i + 1);
      }
    });
  }

  function updateSetNumbers(setsContainer) {
    const rows = setsContainer.querySelectorAll("[data-set-index]");
    rows.forEach(function (row, i) {
      const numberSpan = row.querySelector("span");
      if (numberSpan) {
        numberSpan.textContent = String(i + 1);
      }
    });
  }

  function reindexExercises(container) {
    const blocks = container.querySelectorAll("[data-exercise-index]");
    blocks.forEach(function (block, exIdx) {
      block.setAttribute("data-exercise-index", exIdx);

      const select = block.querySelector("select");
      if (select) {
        select.name = "exercises[" + exIdx + "][exercise_id]";
      }

      const setsContainer = block.querySelector(".sets-container");
      if (setsContainer) {
        setsContainer.setAttribute("data-sets-for", exIdx);
        reindexSets(setsContainer, exIdx);
      }
    });
  }

  function reindexSets(setsContainer, exerciseIndex) {
    if (exerciseIndex === undefined) {
      const exBlock = setsContainer.closest("[data-exercise-index]");
      exerciseIndex = exBlock
        ? exBlock.getAttribute("data-exercise-index")
        : 0;
    }

    const rows = setsContainer.querySelectorAll("[data-set-index]");
    rows.forEach(function (row, setIdx) {
      row.setAttribute("data-set-index", setIdx);

      const inputs = row.querySelectorAll("input");
      inputs.forEach(function (input) {
        const name = input.name;
        if (name.includes("[weight]")) {
          input.name =
            "exercises[" +
            exerciseIndex +
            "][sets][" +
            setIdx +
            "][weight]";
        } else if (name.includes("[reps]")) {
          input.name =
            "exercises[" +
            exerciseIndex +
            "][sets][" +
            setIdx +
            "][reps]";
        }
      });
    });
  }

  function getExerciseOptions() {
    // Try to get exercise options from a hidden data element on the page
    const dataEl = document.getElementById("exercise-options-data");
    if (dataEl) {
      return dataEl.innerHTML;
    }

    // Fallback: try to copy from an existing select
    const existingSelect = document.querySelector(
      'select[name*="[exercise_id]"]'
    );
    if (existingSelect) {
      let options = "";
      for (let i = 0; i < existingSelect.options.length; i++) {
        const opt = existingSelect.options[i];
        if (opt.value) {
          options +=
            '<option value="' + opt.value + '">' + opt.textContent + "</option>";
        }
      }
      return options;
    }

    return "";
  }

  function validateWorkoutForm(form) {
    const exerciseBlocks = form.querySelectorAll("[data-exercise-index]");

    if (exerciseBlocks.length === 0) {
      showToast("At least one exercise is required.", "error");
      return false;
    }

    let valid = true;

    exerciseBlocks.forEach(function (block) {
      const select = block.querySelector("select");
      if (select && !select.value) {
        select.classList.add("border-red-500");
        valid = false;
      } else if (select) {
        select.classList.remove("border-red-500");
      }

      const setRows = block.querySelectorAll("[data-set-index]");
      if (setRows.length === 0) {
        showToast("Each exercise must have at least one set.", "error");
        valid = false;
      }

      setRows.forEach(function (row) {
        const inputs = row.querySelectorAll("input[type='number']");
        inputs.forEach(function (input) {
          const val = parseFloat(input.value);
          if (isNaN(val) || val < 0) {
            input.classList.add("border-red-500");
            valid = false;
          } else {
            input.classList.remove("border-red-500");
          }
        });
      });
    });

    if (!valid) {
      showToast("Please fill in all required fields correctly.", "error");
    }

    return valid;
  }

  // ============================================================
  // Template Form: Dynamic Add/Remove Exercises
  // ============================================================
  let templateExerciseCounter = 0;

  function initTemplateForm() {
    const templateForm = document.getElementById("template-form");
    if (!templateForm) return;

    const exercisesContainer = document.getElementById(
      "template-exercises-container"
    );
    const addExerciseBtn = document.getElementById(
      "template-add-exercise-btn"
    );

    if (!exercisesContainer || !addExerciseBtn) return;

    const existingExercises =
      exercisesContainer.querySelectorAll("[data-template-exercise-index]");
    templateExerciseCounter = existingExercises.length;

    addExerciseBtn.addEventListener("click", function () {
      addTemplateExercise(exercisesContainer);
    });

    exercisesContainer.addEventListener("click", function (e) {
      const target = e.target.closest("[data-action]");
      if (!target) return;

      const action = target.getAttribute("data-action");
      if (action === "remove-template-exercise") {
        removeTemplateExercise(target);
      }
    });

    // Sortable drag-and-drop for exercise reordering
    initDragAndDrop(exercisesContainer);

    if (templateExerciseCounter === 0) {
      addTemplateExercise(exercisesContainer);
    }

    templateForm.addEventListener("submit", function (e) {
      if (!validateTemplateForm(templateForm)) {
        e.preventDefault();
      }
    });
  }

  function addTemplateExercise(container) {
    const index = templateExerciseCounter;
    templateExerciseCounter++;

    const exerciseSelectOptions = getExerciseOptions();

    const row = document.createElement("div");
    row.setAttribute("data-template-exercise-index", index);
    row.className =
      "flex items-center gap-3 bg-white border border-gray-200 rounded-lg p-3 mb-2 shadow-sm";
    row.setAttribute("draggable", "true");

    row.innerHTML =
      '<div class="cursor-grab text-gray-400 flex-shrink-0" aria-label="Drag to reorder">' +
      '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8h16M4 16h16"/></svg>' +
      "</div>" +
      '<span class="text-sm text-gray-500 w-6 text-center flex-shrink-0">' +
      (index + 1) +
      "</span>" +
      '<select name="template_exercises[' +
      index +
      '][exercise_id]" class="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500" required>' +
      '<option value="">Select an exercise</option>' +
      exerciseSelectOptions +
      "</select>" +
      '<input type="hidden" name="template_exercises[' +
      index +
      '][order_index]" value="' +
      index +
      '">' +
      '<button type="button" data-action="remove-template-exercise" class="text-red-400 hover:text-red-600 focus:outline-none flex-shrink-0" aria-label="Remove exercise">' +
      '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>' +
      "</button>";

    container.appendChild(row);
    updateTemplateExerciseNumbers(container);
  }

  function removeTemplateExercise(button) {
    const row = button.closest("[data-template-exercise-index]");
    if (!row) return;

    const container = row.parentElement;
    const rows = container.querySelectorAll("[data-template-exercise-index]");

    if (rows.length <= 1) {
      showToast("At least one exercise is required.", "error");
      return;
    }

    row.remove();
    reindexTemplateExercises(container);
  }

  function updateTemplateExerciseNumbers(container) {
    const rows = container.querySelectorAll("[data-template-exercise-index]");
    rows.forEach(function (row, i) {
      const numberSpan = row.querySelector("span.text-sm");
      if (numberSpan) {
        numberSpan.textContent = String(i + 1);
      }
    });
  }

  function reindexTemplateExercises(container) {
    const rows = container.querySelectorAll("[data-template-exercise-index]");
    rows.forEach(function (row, i) {
      row.setAttribute("data-template-exercise-index", i);

      const select = row.querySelector("select");
      if (select) {
        select.name = "template_exercises[" + i + "][exercise_id]";
      }

      const hiddenInput = row.querySelector('input[type="hidden"]');
      if (hiddenInput) {
        hiddenInput.name = "template_exercises[" + i + "][order_index]";
        hiddenInput.value = String(i);
      }

      const numberSpan = row.querySelector("span.text-sm");
      if (numberSpan) {
        numberSpan.textContent = String(i + 1);
      }
    });
  }

  function validateTemplateForm(form) {
    const nameInput = form.querySelector('input[name="name"]');
    if (nameInput && !nameInput.value.trim()) {
      nameInput.classList.add("border-red-500");
      showToast("Template name is required.", "error");
      return false;
    } else if (nameInput) {
      nameInput.classList.remove("border-red-500");
    }

    const exerciseRows = form.querySelectorAll(
      "[data-template-exercise-index]"
    );
    if (exerciseRows.length === 0) {
      showToast("At least one exercise is required.", "error");
      return false;
    }

    let valid = true;
    exerciseRows.forEach(function (row) {
      const select = row.querySelector("select");
      if (select && !select.value) {
        select.classList.add("border-red-500");
        valid = false;
      } else if (select) {
        select.classList.remove("border-red-500");
      }
    });

    if (!valid) {
      showToast("Please select an exercise for each row.", "error");
    }

    return valid;
  }

  // ============================================================
  // Drag and Drop for Template Exercise Reordering
  // ============================================================
  function initDragAndDrop(container) {
    if (!container) return;

    let draggedItem = null;

    container.addEventListener("dragstart", function (e) {
      draggedItem = e.target.closest("[data-template-exercise-index]");
      if (draggedItem) {
        draggedItem.classList.add("opacity-50");
        e.dataTransfer.effectAllowed = "move";
        e.dataTransfer.setData("text/plain", "");
      }
    });

    container.addEventListener("dragend", function () {
      if (draggedItem) {
        draggedItem.classList.remove("opacity-50");
        draggedItem = null;
      }
      var items = container.querySelectorAll("[data-template-exercise-index]");
      items.forEach(function (item) {
        item.classList.remove("border-t-2", "border-blue-500");
      });
    });

    container.addEventListener("dragover", function (e) {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";

      var target = e.target.closest("[data-template-exercise-index]");
      if (target && target !== draggedItem) {
        var items = container.querySelectorAll(
          "[data-template-exercise-index]"
        );
        items.forEach(function (item) {
          item.classList.remove("border-t-2", "border-blue-500");
        });
        target.classList.add("border-t-2", "border-blue-500");
      }
    });

    container.addEventListener("drop", function (e) {
      e.preventDefault();
      var target = e.target.closest("[data-template-exercise-index]");
      if (target && draggedItem && target !== draggedItem) {
        var allItems = Array.from(
          container.querySelectorAll("[data-template-exercise-index]")
        );
        var draggedIdx = allItems.indexOf(draggedItem);
        var targetIdx = allItems.indexOf(target);

        if (draggedIdx < targetIdx) {
          container.insertBefore(draggedItem, target.nextSibling);
        } else {
          container.insertBefore(draggedItem, target);
        }

        reindexTemplateExercises(container);
      }
    });
  }

  // ============================================================
  // Calendar View Interactions
  // ============================================================
  function initCalendarView() {
    const calendarContainer = document.getElementById("calendar-container");
    if (!calendarContainer) return;

    const calendarDays = calendarContainer.querySelectorAll("[data-date]");
    calendarDays.forEach(function (day) {
      day.addEventListener("click", function () {
        const date = this.getAttribute("data-date");
        if (date) {
          // Navigate to workout log for that date or show details
          const hasWorkout = this.getAttribute("data-has-workout") === "true";
          if (hasWorkout) {
            const workoutId = this.getAttribute("data-workout-id");
            if (workoutId) {
              window.location.href = "/workouts/" + workoutId;
            }
          } else {
            window.location.href = "/workouts/new?date=" + date;
          }
        }
      });

      day.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          this.click();
        }
      });
    });

    // Month navigation
    const prevMonthBtn = document.getElementById("calendar-prev-month");
    const nextMonthBtn = document.getElementById("calendar-next-month");

    if (prevMonthBtn) {
      prevMonthBtn.addEventListener("click", function () {
        navigateCalendar(-1);
      });
    }

    if (nextMonthBtn) {
      nextMonthBtn.addEventListener("click", function () {
        navigateCalendar(1);
      });
    }
  }

  function navigateCalendar(direction) {
    const currentMonthEl = document.getElementById("calendar-current-month");
    if (!currentMonthEl) return;

    const currentYear = parseInt(
      currentMonthEl.getAttribute("data-year"),
      10
    );
    const currentMonth = parseInt(
      currentMonthEl.getAttribute("data-month"),
      10
    );

    let newMonth = currentMonth + direction;
    let newYear = currentYear;

    if (newMonth < 1) {
      newMonth = 12;
      newYear--;
    } else if (newMonth > 12) {
      newMonth = 1;
      newYear++;
    }

    const params = new URLSearchParams(window.location.search);
    params.set("year", newYear);
    params.set("month", newMonth);
    window.location.href =
      window.location.pathname + "?" + params.toString();
  }

  // ============================================================
  // Form Validation Helpers
  // ============================================================
  function initFormValidation() {
    // Registration form validation
    const registerForm = document.getElementById("register-form");
    if (registerForm) {
      registerForm.addEventListener("submit", function (e) {
        if (!validateRegistrationForm(registerForm)) {
          e.preventDefault();
        }
      });
    }

    // Login form validation
    const loginForm = document.getElementById("login-form");
    if (loginForm) {
      loginForm.addEventListener("submit", function (e) {
        if (!validateLoginForm(loginForm)) {
          e.preventDefault();
        }
      });
    }

    // Measurement form validation
    const measurementForm = document.getElementById("measurement-form");
    if (measurementForm) {
      measurementForm.addEventListener("submit", function (e) {
        if (!validateMeasurementForm(measurementForm)) {
          e.preventDefault();
        }
      });
    }

    // Real-time validation feedback
    document
      .querySelectorAll("input[required], select[required]")
      .forEach(function (input) {
        input.addEventListener("blur", function () {
          validateField(this);
        });
        input.addEventListener("input", function () {
          if (this.classList.contains("border-red-500")) {
            validateField(this);
          }
        });
      });
  }

  function validateField(field) {
    let valid = true;

    if (field.hasAttribute("required") && !field.value.trim()) {
      valid = false;
    }

    if (field.type === "email" && field.value) {
      var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(field.value)) {
        valid = false;
      }
    }

    if (field.type === "number" && field.value) {
      var num = parseFloat(field.value);
      var min = field.hasAttribute("min")
        ? parseFloat(field.getAttribute("min"))
        : -Infinity;
      var max = field.hasAttribute("max")
        ? parseFloat(field.getAttribute("max"))
        : Infinity;
      if (isNaN(num) || num < min || num > max) {
        valid = false;
      }
    }

    if (field.hasAttribute("minlength") && field.value) {
      var minLen = parseInt(field.getAttribute("minlength"), 10);
      if (field.value.length < minLen) {
        valid = false;
      }
    }

    if (valid) {
      field.classList.remove("border-red-500");
      field.classList.add("border-gray-300");
      hideFieldError(field);
    } else {
      field.classList.remove("border-gray-300");
      field.classList.add("border-red-500");
    }

    return valid;
  }

  function validateRegistrationForm(form) {
    var valid = true;

    var displayName = form.querySelector('input[name="display_name"]');
    var email = form.querySelector('input[name="email"]');
    var username = form.querySelector('input[name="username"]');
    var password = form.querySelector('input[name="password"]');
    var confirmPassword = form.querySelector(
      'input[name="confirm_password"]'
    );

    if (displayName && !displayName.value.trim()) {
      showFieldError(displayName, "Display name is required.");
      valid = false;
    }

    if (email && !email.value.trim()) {
      showFieldError(email, "Email is required.");
      valid = false;
    } else if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value)) {
      showFieldError(email, "Please enter a valid email address.");
      valid = false;
    }

    if (username && !username.value.trim()) {
      showFieldError(username, "Username is required.");
      valid = false;
    } else if (username && username.value.length < 3) {
      showFieldError(username, "Username must be at least 3 characters.");
      valid = false;
    }

    if (password && !password.value) {
      showFieldError(password, "Password is required.");
      valid = false;
    } else if (password && password.value.length < 8) {
      showFieldError(password, "Password must be at least 8 characters.");
      valid = false;
    }

    if (confirmPassword && password && confirmPassword.value !== password.value) {
      showFieldError(confirmPassword, "Passwords do not match.");
      valid = false;
    }

    if (!valid) {
      showToast("Please fix the errors in the form.", "error");
    }

    return valid;
  }

  function validateLoginForm(form) {
    var valid = true;

    var username = form.querySelector('input[name="username"]');
    var password = form.querySelector('input[name="password"]');

    if (username && !username.value.trim()) {
      showFieldError(username, "Username is required.");
      valid = false;
    }

    if (password && !password.value) {
      showFieldError(password, "Password is required.");
      valid = false;
    }

    return valid;
  }

  function validateMeasurementForm(form) {
    var valid = true;

    var dateInput = form.querySelector('input[name="measurement_date"]');
    if (dateInput && !dateInput.value) {
      showFieldError(dateInput, "Date is required.");
      valid = false;
    }

    // At least one measurement field should be filled
    var measurementFields = [
      "weight",
      "body_fat_percent",
      "chest",
      "waist",
      "hips",
      "arms",
      "thighs",
    ];
    var hasValue = false;
    measurementFields.forEach(function (fieldName) {
      var input = form.querySelector('input[name="' + fieldName + '"]');
      if (input && input.value) {
        hasValue = true;
        var val = parseFloat(input.value);
        if (isNaN(val) || val < 0) {
          showFieldError(input, "Please enter a valid positive number.");
          valid = false;
        }
      }
    });

    if (!hasValue) {
      showToast("Please enter at least one measurement.", "error");
      valid = false;
    }

    return valid;
  }

  function showFieldError(field, message) {
    field.classList.remove("border-gray-300");
    field.classList.add("border-red-500");

    var existingError = field.parentElement.querySelector(".field-error");
    if (existingError) {
      existingError.textContent = message;
      return;
    }

    var errorEl = document.createElement("p");
    errorEl.className = "field-error text-red-500 text-xs mt-1";
    errorEl.textContent = message;
    field.parentElement.appendChild(errorEl);
  }

  function hideFieldError(field) {
    var errorEl = field.parentElement.querySelector(".field-error");
    if (errorEl) {
      errorEl.remove();
    }
  }

  // ============================================================
  // Toast Notifications
  // ============================================================
  function showToast(message, type) {
    type = type || "info";

    var existingToast = document.getElementById("toast-notification");
    if (existingToast) {
      existingToast.remove();
    }

    var toast = document.createElement("div");
    toast.id = "toast-notification";
    toast.className =
      "fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium transition-all duration-300 transform translate-x-full";

    if (type === "error") {
      toast.className += " bg-red-500 text-white";
    } else if (type === "success") {
      toast.className += " bg-green-500 text-white";
    } else {
      toast.className += " bg-blue-500 text-white";
    }

    toast.textContent = message;

    var closeBtn = document.createElement("button");
    closeBtn.className = "ml-3 text-white hover:text-gray-200 font-bold";
    closeBtn.innerHTML = "&times;";
    closeBtn.addEventListener("click", function () {
      dismissToast(toast);
    });
    toast.appendChild(closeBtn);

    document.body.appendChild(toast);

    // Animate in
    requestAnimationFrame(function () {
      toast.classList.remove("translate-x-full");
      toast.classList.add("translate-x-0");
    });

    // Auto dismiss after 4 seconds
    setTimeout(function () {
      dismissToast(toast);
    }, 4000);
  }

  function dismissToast(toast) {
    if (!toast || !toast.parentElement) return;
    toast.classList.remove("translate-x-0");
    toast.classList.add("translate-x-full");
    setTimeout(function () {
      if (toast.parentElement) {
        toast.remove();
      }
    }, 300);
  }

  // ============================================================
  // Sticky Bottom Bar Behavior on Mobile
  // ============================================================
  function initStickyBottomBar() {
    var bottomBar = document.getElementById("sticky-bottom-bar");
    if (!bottomBar) return;

    var lastScrollY = window.scrollY;
    var ticking = false;

    function updateBottomBar() {
      var currentScrollY = window.scrollY;

      if (currentScrollY > lastScrollY && currentScrollY > 100) {
        // Scrolling down - hide bottom bar
        bottomBar.classList.add("translate-y-full");
        bottomBar.classList.remove("translate-y-0");
      } else {
        // Scrolling up - show bottom bar
        bottomBar.classList.remove("translate-y-full");
        bottomBar.classList.add("translate-y-0");
      }

      lastScrollY = currentScrollY;
      ticking = false;
    }

    window.addEventListener(
      "scroll",
      function () {
        if (!ticking) {
          requestAnimationFrame(updateBottomBar);
          ticking = true;
        }
      },
      { passive: true }
    );
  }

  // ============================================================
  // Confirm Delete Dialogs
  // ============================================================
  function initDeleteConfirmations() {
    document.addEventListener("click", function (e) {
      var deleteBtn = e.target.closest("[data-confirm-delete]");
      if (!deleteBtn) return;

      var message =
        deleteBtn.getAttribute("data-confirm-delete") ||
        "Are you sure you want to delete this item? This action cannot be undone.";

      if (!confirm(message)) {
        e.preventDefault();
        e.stopPropagation();
      }
    });
  }

  // ============================================================
  // Auto-dismiss Flash Messages
  // ============================================================
  function initFlashMessages() {
    var flashMessages = document.querySelectorAll("[data-flash-message]");
    flashMessages.forEach(function (msg) {
      setTimeout(function () {
        msg.classList.add("opacity-0", "transition-opacity", "duration-500");
        setTimeout(function () {
          msg.remove();
        }, 500);
      }, 5000);

      var closeBtn = msg.querySelector("[data-dismiss-flash]");
      if (closeBtn) {
        closeBtn.addEventListener("click", function () {
          msg.remove();
        });
      }
    });
  }

  // ============================================================
  // Save as Template Checkbox Toggle
  // ============================================================
  function initSaveAsTemplate() {
    var checkbox = document.getElementById("save-as-template-checkbox");
    var templateNameGroup = document.getElementById("template-name-group");

    if (!checkbox || !templateNameGroup) return;

    function toggleTemplateNameVisibility() {
      if (checkbox.checked) {
        templateNameGroup.classList.remove("hidden");
        var nameInput = templateNameGroup.querySelector("input");
        if (nameInput) {
          nameInput.setAttribute("required", "required");
        }
      } else {
        templateNameGroup.classList.add("hidden");
        var nameInput = templateNameGroup.querySelector("input");
        if (nameInput) {
          nameInput.removeAttribute("required");
          nameInput.value = "";
        }
      }
    }

    checkbox.addEventListener("change", toggleTemplateNameVisibility);
    toggleTemplateNameVisibility();
  }

  // ============================================================
  // Exercise Search/Filter
  // ============================================================
  function initExerciseSearch() {
    var searchInput = document.getElementById("exercise-search-input");
    var muscleGroupFilter = document.getElementById("muscle-group-filter");
    var equipmentFilter = document.getElementById("equipment-filter");

    if (!searchInput && !muscleGroupFilter && !equipmentFilter) return;

    function applyFilters() {
      var params = new URLSearchParams();

      if (searchInput && searchInput.value.trim()) {
        params.set("q", searchInput.value.trim());
      }
      if (muscleGroupFilter && muscleGroupFilter.value) {
        params.set("muscle_group", muscleGroupFilter.value);
      }
      if (equipmentFilter && equipmentFilter.value) {
        params.set("equipment", equipmentFilter.value);
      }

      var queryString = params.toString();
      window.location.href =
        window.location.pathname + (queryString ? "?" + queryString : "");
    }

    var debounceTimer = null;

    if (searchInput) {
      searchInput.addEventListener("input", function () {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(applyFilters, 500);
      });

      searchInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
          e.preventDefault();
          clearTimeout(debounceTimer);
          applyFilters();
        }
      });
    }

    if (muscleGroupFilter) {
      muscleGroupFilter.addEventListener("change", applyFilters);
    }

    if (equipmentFilter) {
      equipmentFilter.addEventListener("change", applyFilters);
    }
  }

  // ============================================================
  // Load Template into Workout Form
  // ============================================================
  function initTemplateLoader() {
    var templateSelect = document.getElementById("load-template-select");
    var loadTemplateBtn = document.getElementById("load-template-btn");

    if (!templateSelect || !loadTemplateBtn) return;

    loadTemplateBtn.addEventListener("click", function () {
      var templateId = templateSelect.value;
      if (!templateId) {
        showToast("Please select a template.", "error");
        return;
      }

      var currentUrl = new URL(window.location.href);
      currentUrl.searchParams.set("template_id", templateId);
      window.location.href = currentUrl.toString();
    });
  }

  // ============================================================
  // Number Input Stepper (for mobile-friendly +/- buttons)
  // ============================================================
  function initNumberSteppers() {
    document.addEventListener("click", function (e) {
      var stepperBtn = e.target.closest("[data-stepper]");
      if (!stepperBtn) return;

      var direction = stepperBtn.getAttribute("data-stepper");
      var inputId = stepperBtn.getAttribute("data-stepper-target");
      var input = document.getElementById(inputId);

      if (!input) {
        // Try finding sibling input
        var parent = stepperBtn.parentElement;
        input = parent ? parent.querySelector('input[type="number"]') : null;
      }

      if (!input) return;

      var currentVal = parseFloat(input.value) || 0;
      var step = parseFloat(input.getAttribute("step")) || 1;
      var min = input.hasAttribute("min")
        ? parseFloat(input.getAttribute("min"))
        : -Infinity;
      var max = input.hasAttribute("max")
        ? parseFloat(input.getAttribute("max"))
        : Infinity;

      var newVal;
      if (direction === "up") {
        newVal = Math.min(currentVal + step, max);
      } else {
        newVal = Math.max(currentVal - step, min);
      }

      // Round to avoid floating point issues
      input.value = Math.round(newVal * 100) / 100;
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
  }

  // ============================================================
  // Progress Chart Data Preparation
  // ============================================================
  function initProgressCharts() {
    var chartContainers = document.querySelectorAll("[data-chart]");
    if (chartContainers.length === 0) return;

    chartContainers.forEach(function (container) {
      var chartType = container.getAttribute("data-chart");
      var dataEl = container.querySelector("[data-chart-data]");

      if (!dataEl) return;

      try {
        var data = JSON.parse(dataEl.textContent);
        renderSimpleChart(container, chartType, data);
      } catch (err) {
        console.error("Failed to parse chart data:", err);
      }
    });
  }

  function renderSimpleChart(container, type, data) {
    // Simple bar/line chart rendering using CSS
    if (!data || !data.labels || !data.values) return;

    var maxVal = Math.max.apply(null, data.values);
    if (maxVal === 0) maxVal = 1;

    var chartEl = document.createElement("div");
    chartEl.className = "flex items-end gap-1 h-40 mt-2";

    data.values.forEach(function (val, i) {
      var barWrapper = document.createElement("div");
      barWrapper.className =
        "flex flex-col items-center flex-1 min-w-0";

      var bar = document.createElement("div");
      var heightPercent = (val / maxVal) * 100;
      bar.className =
        "w-full rounded-t transition-all duration-300 " +
        (type === "volume" ? "bg-blue-500" : "bg-green-500");
      bar.style.height = Math.max(heightPercent, 2) + "%";
      bar.title = (data.labels[i] || "") + ": " + val;

      var label = document.createElement("span");
      label.className =
        "text-xs text-gray-500 mt-1 truncate w-full text-center";
      label.textContent = data.labels[i] || "";

      barWrapper.appendChild(bar);
      barWrapper.appendChild(label);
      chartEl.appendChild(barWrapper);
    });

    // Clear existing chart content (but keep data element)
    var existingChart = container.querySelector(".chart-rendered");
    if (existingChart) {
      existingChart.remove();
    }

    chartEl.className += " chart-rendered";
    container.appendChild(chartEl);
  }

  // ============================================================
  // Initialization
  // ============================================================
  function init() {
    initHamburgerMenu();
    initWorkoutForm();
    initTemplateForm();
    initCalendarView();
    initFormValidation();
    initStickyBottomBar();
    initDeleteConfirmations();
    initFlashMessages();
    initSaveAsTemplate();
    initExerciseSearch();
    initTemplateLoader();
    initNumberSteppers();
    initProgressCharts();
  }

  // Run on DOM ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // Expose showToast globally for use in templates
  window.FitLog = {
    showToast: showToast,
  };
})();