"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertCircle, Loader2, ShieldCheck } from "lucide-react";
import { useParams } from "next/navigation";

import { api } from "@/lib/api";
import type { Verificacao } from "@/lib/tipos";

/** Pagina publica de verificacao — o destino do QR carimbado no PDF.
 *
 * Fica fora do grupo `[tenant]/(app)`: quem chega aqui nao tem login, nao
 * sabe o slug do escritorio e nao pode ver a barra lateral do sistema.
 */
export default function VerificarPage() {
  const { codigo } = useParams<{ codigo: string }>();

  const { data, isLoading, isError } = useQuery<Verificacao>({
    queryKey: ["verificacao", codigo],
    queryFn: async () => (await api.get(`/api/verificar/${codigo}`)).data,
    retry: false,
  });

  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="w-full max-w-lg">
        <p className="mb-4 text-center text-sm font-medium tracking-wide text-navy">
          MayaAssinador
        </p>

        {isLoading && (
          <div className="cartao flex items-center justify-center gap-2 p-10 text-sm text-dark/65">
            <Loader2 className="h-4 w-4 animate-spin" />
            Verificando documento...
          </div>
        )}

        {isError && <NaoEncontrado codigo={codigo} />}

        {data && <Autentico dados={data} />}

        <p className="mt-6 text-center text-xs text-dark/55">
          Esta pagina confirma a origem do documento. Ela nao permite baixar o
          arquivo — quem verifica ja o tem em maos.
        </p>
      </div>
    </main>
  );
}

function Autentico({ dados }: { dados: Verificacao }) {
  return (
    <div className="cartao overflow-hidden">
      <div className="flex items-center gap-3 border-b border-dark/[.06] bg-teal/[.07] px-6 py-5">
        <ShieldCheck className="h-7 w-7 shrink-0 text-teal" />
        <div>
          <p className="text-base font-semibold text-dark">Documento autentico</p>
          <p className="text-xs text-dark/65">
            Emitido por {dados.escritorio}
          </p>
        </div>
      </div>

      <dl className="divide-y divide-dark/[.06] px-6">
        <Linha rotulo="Codigo" valor={dados.codigo} mono />
        <Linha rotulo="Arquivo" valor={dados.nome_arquivo} />
        {dados.signatario && (
          <Linha
            rotulo="Signatario"
            valor={
              dados.signatario_oab
                ? `${dados.signatario} — OAB ${dados.signatario_oab}`
                : dados.signatario
            }
          />
        )}
        {dados.assinado_em && (
          <Linha rotulo="Assinado em" valor={formatarData(dados.assinado_em)} />
        )}
        {dados.paginas != null && (
          <Linha
            rotulo="Paginas"
            valor={`${dados.paginas} ${dados.paginas === 1 ? "pagina" : "paginas"}`}
          />
        )}
        {dados.hash_sha256 && (
          <Linha rotulo="Hash SHA-256" valor={dados.hash_sha256} mono quebrar />
        )}
      </dl>

      {dados.hash_sha256 && (
        <p className="border-t border-dark/[.06] bg-cinza px-6 py-4 text-xs text-dark/65">
          Para conferir por conta propria, gere o hash do PDF que voce recebeu e
          compare com o valor acima. Se baterem, o arquivo nao foi alterado
          desde a assinatura.
        </p>
      )}
    </div>
  );
}

function NaoEncontrado({ codigo }: { codigo: string }) {
  return (
    <div className="cartao p-6">
      <div className="flex items-center gap-3">
        <AlertCircle className="h-7 w-7 shrink-0 text-amber" />
        <div>
          <p className="text-base font-semibold text-dark">
            Documento nao encontrado
          </p>
          <p className="text-xs text-dark/65">
            Nenhum documento corresponde ao codigo{" "}
            <span className="font-mono">{codigo}</span>.
          </p>
        </div>
      </div>

      <p className="mt-4 text-sm text-dark/75">
        Confira o codigo impresso ao lado do QR, no rodape da ultima pagina. Ele
        tem oito caracteres, no formato <span className="font-mono">AAAA-BBBB</span>.
      </p>
    </div>
  );
}

function Linha({
  rotulo,
  valor,
  mono = false,
  quebrar = false,
}: {
  rotulo: string;
  valor: string;
  mono?: boolean;
  quebrar?: boolean;
}) {
  return (
    <div className="flex flex-col gap-0.5 py-3 sm:flex-row sm:gap-4 sm:py-3.5">
      <dt className="shrink-0 text-xs uppercase tracking-wide text-dark/55 sm:w-32 sm:pt-0.5">
        {rotulo}
      </dt>
      <dd
        className={[
          "min-w-0 text-sm text-dark",
          mono ? "font-mono" : "",
          quebrar ? "break-all text-xs" : "",
        ].join(" ")}
      >
        {valor}
      </dd>
    </div>
  );
}

function formatarData(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
