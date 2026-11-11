// Mirrors the backend rule (app/security.py password_strength_error):
// at least 6 characters.
export const MIN_PASSWORD_LENGTH = 6;

export function isStrongPassword(password: string): boolean {
  return password.length >= MIN_PASSWORD_LENGTH;
}
