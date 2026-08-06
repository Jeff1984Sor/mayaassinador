"use client";

import { Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

/** Entrada manual do codigo — para quem esta com o papel na mao e sem
 *  como ler o QR. O codigo e curto justamente para ser digitado ou ditado
 *  por telefone. */
export default function VerificarEntradaPage() {
  const router = useRouter();
  const [codigo, setCodigo] = useState("");

  const limpo = codigo.replace(/[^0-9a-fA-F]/g, "").toUpperCase();
  const valido = limpo.length === 8;

  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <p className="mb-4 text-center text-sm font-medium tracking-wide text-navy">
          MayaAssinador
        </p>

        <form
          className="cartao p-6"
          onSubmit={(e) => {
            e.preventDefault();
            if (valido) router.push(`/verificar/${limpo}`);
          }}
        >
          <h1 className="text-base font-semibold text-dark">
            Verificar documento
          </h1>
          <p className="mt-1 text-sm text-dark/65">
            Digite o codigo impresso ao lado do QR, no rodape da ultima pagina.
          </p>

          <label className="rotulo mt-5" htmlFor="codigo">
            Codigo de verificacao
          </label>
          <input
            id="codigo"
            className="campo font-mono uppercase tracking-widest"
            placeholder="AAAA-BBBB"
            autoComplete="off"
            autoFocus
            maxLength={9}
            value={codigo}
            onChange={(e) => setCodigo(e.target.value)}
          />

          <button
            type="submit"
            className="btn-primario mt-4 w-full disabled:opacity-50"
            disabled={!valido}
          >
            <Search className="h-4 w-4" />
            Verificar
          </button>
        </form>
      </div>
    </main>
  );
}
