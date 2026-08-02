/** Join class names, dropping falsy values. */
export default function cn(...parts) {
  return parts.filter(Boolean).join(' ')
}
