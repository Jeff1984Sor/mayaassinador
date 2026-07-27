"use client";

import { Settings } from "lucide-react";

export default function ConfiguracoesPage() {
  return (
    <div className="px-8 py-7">
      <header className="mb-7">
        <h1 className="text-xl font-semibold tracking-tight text-dark">
          Configuracoes
        </h1>
        <p className="mt-1 text-sm text-dark/55">
          Dados do escritorio, cabecalho, rodape, rubrica, assinatura e email.
        </p>
      </header>

      <div className="cartao flex flex-col items-center justify-center px-6 py-20 text-center">
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-cinza">
          <Settings className="h-6 w-6 text-navy/50" />
        </div>
        <h2 className="text-base font-medium text-dark">Chega na F2</h2>
        <p className="mt-1.5 max-w-sm text-sm text-dark/50">
          Abas, preview A4 ao vivo e o botao &quot;Gerar PDF de teste&quot;.
        </p>
      </div>
    </div>
  );
}
