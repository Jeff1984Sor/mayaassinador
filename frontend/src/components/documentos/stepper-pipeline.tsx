"use client";

import { AlertCircle, Check, Loader2 } from "lucide-react";

import { ETAPAS, type DocumentoDetalhe } from "@/lib/documentos";
import { cn } from "@/lib/utils";

/**
 * Stepper do processamento. As etapas acendem conforme os eventos de
 * auditoria chegam do backend — nao ha simulacao no frontend, o que se ve
 * aqui e o que de fato aconteceu com o arquivo.
 */
export function StepperPipeline({ doc }: { doc: DocumentoDetalhe }) {
  const concluidas = new Set(doc.eventos?.map((e) => e.tipo) ?? []);
  const comErro = doc.status === "erro";

  // rubrica so faz parte do fluxo se o documento foi marcado para rubricar
  const etapas = ETAPAS.filter(
    (e) => e.chave !== "rubrica_aplicada" || doc.rubricado,
  );

  const indiceAtual = etapas.findIndex((e) => !concluidas.has(e.chave));

  return (
    <ol className="space-y-1">
      {etapas.map((etapa, i) => {
        const feita = concluidas.has(etapa.chave);
        const atual = !feita && i === indiceAtual && !comErro;
        const falhou = comErro && i === indiceAtual;

        return (
          <li key={etapa.chave} className="flex items-center gap-3 py-1.5">
            <span
              className={cn(
                "flex h-7 w-7 shrink-0 items-center justify-center rounded-full border transition-all duration-300",
                feita && "border-teal bg-teal text-white",
                atual && "border-amber bg-amber/10 text-amber",
                falhou && "border-risco bg-risco/10 text-risco",
                !feita && !atual && !falhou && "border-dark/12 text-dark/45",
              )}
            >
              {feita ? (
                <Check className="h-3.5 w-3.5" strokeWidth={3} />
              ) : atual ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : falhou ? (
                <AlertCircle className="h-3.5 w-3.5" />
              ) : (
                <span className="text-[11px] font-medium">{i + 1}</span>
              )}
            </span>

            <span
              className={cn(
                "text-sm transition-colors",
                feita && "text-dark/92",
                atual && "font-medium text-dark",
                falhou && "font-medium text-risco",
                !feita && !atual && !falhou && "text-dark/55",
              )}
            >
              {etapa.rotulo}
            </span>

            {i < etapas.length - 1 && (
              <span
                className={cn(
                  "ml-auto h-px flex-1 transition-colors",
                  feita ? "bg-teal/30" : "bg-dark/[.06]",
                )}
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}
