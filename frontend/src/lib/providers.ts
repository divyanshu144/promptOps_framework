export const providers = [
  { id: "ollama", label: "Ollama", model: "llama3.1" },
  { id: "openai", label: "OpenAI", model: "gpt-4o-mini" },
  { id: "anthropic", label: "Claude (Anthropic)", model: "claude-haiku-4-5-20251001" },
  { id: "mistral", label: "Mistral", model: "mistral-small-latest" },
];
export function defaultModel(provider: string): string {
  return providers.find((item) => item.id === provider)?.model || "llama3.1";
}
