// Versão mínima do boilerplate Lovable, só para o build funcionar fora do Lovable.
// Em um projeto Lovable este arquivo é substituído pelo original.
let last: Error | undefined;

if (typeof process !== "undefined" && typeof process.on === "function") {
  process.on("uncaughtException", (e) => {
    last = e;
  });
}

export function consumeLastCapturedError(): Error | undefined {
  const e = last;
  last = undefined;
  return e;
}
