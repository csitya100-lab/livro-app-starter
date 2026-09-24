// Versão mínima do boilerplate Lovable, só para o build funcionar fora do Lovable.
export function renderErrorPage(): string {
  return `<!doctype html><html><head><meta charset="utf-8"><title>Erro</title></head>
<body style="font-family:system-ui;padding:2rem"><h1>A página não carregou</h1>
<p>Algo deu errado no servidor. Tente recarregar.</p></body></html>`;
}
