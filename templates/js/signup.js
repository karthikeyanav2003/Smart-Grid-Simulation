document.addEventListener("DOMContentLoaded", function () {
    const toStep2Btn = document.getElementById("toStep2");
    const backToStep1Btn = document.getElementById("backToStep1");
    const signupForm = document.getElementById("signupForm");
    
    const formStep1 = document.getElementById("formStep1");
    const formStep2 = document.getElementById("formStep2");
    const progressBarFill = document.getElementById("progressBarFill");

    // Error elements
    const firstName = document.getElementById("firstname");
    const lastName = document.getElementById("lastname");
    const email = document.getElementById("email");
    const dob = document.getElementById("dob");

    // Function to validate Step 1
    function validateStep1() {
        let isValid = true;

        if (firstName.value.trim() === "") {
            document.getElementById("firstname-error").style.display = "block";
            isValid = false;
        } else {
            document.getElementById("firstname-error").style.display = "none";
        }

        if (lastName.value.trim() === "") {
            document.getElementById("lastname-error").style.display = "block";
            isValid = false;
        } else {
            document.getElementById("lastname-error").style.display = "none";
        }

        if (email.value.trim() === "" || !email.value.includes("@")) {
            document.getElementById("email-error").style.display = "block";
            isValid = false;
        } else {
            document.getElementById("email-error").style.display = "none";
        }

        if (dob.value.trim() === "") {
            document.getElementById("dob-error").style.display = "block";
            isValid = false;
        } else {
            document.getElementById("dob-error").style.display = "none";
        }

        return isValid;
    }

    // Move to Step 2
    toStep2Btn.addEventListener("click", function () {
        if (validateStep1()) {
            formStep1.classList.remove("active");
            formStep2.classList.add("active");

            progressBarFill.style.width = "100%";
            document.getElementById("step2").classList.add("active");
        }
    });

    // Move back to Step 1
    backToStep1Btn.addEventListener("click", function () {
        formStep2.classList.remove("active");
        formStep1.classList.add("active");

        progressBarFill.style.width = "50%";
        document.getElementById("step2").classList.remove("active");
    });

    // Prevent form submission if passwords don't match
    signupForm.addEventListener("submit", function (e) {
        const password = document.getElementById("password").value;
        const confirmPassword = document.getElementById("confirm_password").value;

        if (password !== confirmPassword) {
            document.getElementById("confirm-password-error").style.display = "block";
            e.preventDefault();
        } else {
            document.getElementById("confirm-password-error").style.display = "none";
        }
    });
});
