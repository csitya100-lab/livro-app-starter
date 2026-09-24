// Versão mínima do boilerplate Lovable, só para o build funcionar fora do Lovable.
export function reportLovableError(error: unknown, context?: Record<string, unknown>) {
  console.error("[app-error]", error, context);
}
