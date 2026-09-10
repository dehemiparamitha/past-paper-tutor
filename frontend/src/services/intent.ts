const questionSearchPatterns = [
  /\bfind\b.*\bquestions?\b/i,
  /\blist\b.*\bquestions?\b/i,
  /\bshow\b.*\bquestions?\b/i,
  /\bquestions?\s+(about|on|related to)\b/i,
  /\b(similar|related)\s+questions?\b/i,
]

export function isQuestionSearchRequest(input: string): boolean {
  return questionSearchPatterns.some((pattern) => pattern.test(input))
}
