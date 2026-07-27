"use client";

import { useQuery } from "@tanstack/react-query";
import { FileSignature } from "lucide-react";

import { api } from "@/lib/api";

export default function DocumentosPage() {
  // Chamada real ao backend: prova que o token do Zustand chega na API.
  const { data: me } = useQuery({
    queryKey: ["me"],
    queryFn: async () => (await api.get("/api/auth/me")).data,
  });

  return (
    <div className="px-8 py-7">
      <header className="mb-7">
        <h1 className="text-xl font-semibold tracking-tight text-dark">
          Documentos
        </h1>
        <p className="mt-1 text-sm text-dark/55">
          Envie um .docx e receba o PDF timbrado, rubricado e assinado.
        </p>
      </header>

      <div className="cartao flex flex-col items-center justify-center px-6 py-20 text-center">
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-cinza">
          <FileSignature className="h-6 w-6 text-navy/50" />
        </div>
        <h2 className="text-base font-medium text-dark">
          O CRUD de documentos chega na F4
        </h2>
        <p className="mt-1.5 max-w-sm text-sm text-dark/50">
          A fundacao esta no ar: autenticacao, tenant e API respondendo.
          Proxima parada e a tela de Configuracoes (F2).
        </p>

        {me && (
          <p className="mt-6 rounded-lg bg-teal/10 px-3 py-2 font-mono text-xs text-teal">
            conectado como {me.email} · tenant {me.tenant_slug}
          </p>
        )}
      </div>
    </div>
  );
}
