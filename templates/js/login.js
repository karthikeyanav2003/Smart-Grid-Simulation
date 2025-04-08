// Login form validation
document.getElementById('loginForm').addEventListener('submit', function(e) {
  let valid = true;
  const email = document.getElementById('email').value;
  const password = document.getElementById('password').value;
  
  // Reset error messages
  document.querySelectorAll('.error-message').forEach(elem => {
    elem.style.display = 'none';
  });
  
  // Validate email
  if (!email || !validateEmail(email)) {
    document.getElementById('email-error').style.display = 'block';
    valid = false;
  }
  
  // Validate password
  if (!password) {
    document.getElementById('password-error').style.display = 'block';
    valid = false;
  }
  
  // Prevent form submission if validation fails
  if (!valid) {
    e.preventDefault();
  }
});

// Simple email validation function
function validateEmail(email) {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(email);
}