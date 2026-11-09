// Mirrors the backend rule (app/security.py password_strength_error):
// at least 10 characters with an upper-case letter, a lower-case letter and a digit.
export const MIN_PASSWORD_LENGTH = 10;

export function isStrongPassword(password: string): boolean {
  return (
    password.length >= MIN_PASSWORD_LENGTH &&
    /\p{Lu}/u.test(password) &&
    /\p{Ll}/u.test(password) &&
    /\d/.test(password)
  );
}
