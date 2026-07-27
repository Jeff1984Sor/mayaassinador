"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangle, Loader2, Send, X } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { api, mensagemErro } from "@/lib/api";
import type { Documento } from "@/lib/documentos";
import { cn } from "@/lib/utils";

type Padrao = {
  assunto: string;
  mensagem: string;
  remetente_nome: string;
  remetente_email: string;
  smtp_configurado: boolean;
};

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function ModalEmail({
  tenant,
  doc,
  aoEnviado,
  aoFechar,
}: {
  tenant: string;
  doc: Documento;
  aoEnviado: () => void;
  aoFechar: () => void;
}) {
  const [destinatarios, setDestinatarios] = useState<string[]>([]);
  const [entrada, setEntrada] = useState("");
  const [assunto, setAssunto] = useState("");
  const [mensagem, setMensagem] = useState("");
  const [remetenteNome, setRemetenteNome] = useState("");
  const [remetenteEmail, setRemetenteEmail] = useState("");
  const [emailContaSmtp, setEmailContaSmtp] = useState("");

  const { data: padrao, isLoading } = useQuery<Padrao>({
    queryKey: ["email-padrao", tenant, doc.id],
    queryFn: async () =>
      (await api.get(`/api/${tenant}/documentos/${doc.id}/email-padrao`)).data,
  });

  useEffect(() => {
    if (!padrao) return;
    setAssunto(padrao.assunto);
    setMensagem(padrao.mensagem);
    setRemetenteNome(padrao.remetente_nome);
    setRemetenteEmail(padrao.remetente_email);
    setEmailContaSmtp(padrao.remetente_email);
  }, [padrao]);

  function adicionar(valor: string) {
    const email = valor.trim().replace(/,$/, "");
    if (!email) return;
    if (!EMAIL_RE.test(email)) {
      toast.error(`"${email}" nao e um email valido`);
      return;
    }
    if (destinatarios.includes(email)) {
      setEntrada("");
      return;
    }
    setDestinatarios([...destinatarios, email]);
    setEntrada("");
  }

  const enviar = useMutation({
    mutationFn: async () =>
      (
        await api.post(`/api/${tenant}/documentos/${doc.id}/enviar-email`, {
          destinatarios,
          assunto,
          mensagem,
          remetente_nome: remetenteNome || null,
          remetente_email: remetenteEmail || null,
        })
      ).data,
    onSuccess: () => {
      toast.success(
        `Enviado para ${destinatarios.length} destinatario${destinatarios.length === 1 ? "" : "s"}`,
      );
      aoEnviado();
    },
    onError: (e) => toast.error(mensagemErro(e, "Falha ao enviar o email")),
  });

  const remetenteAlterado =
    !!emailContaSmtp && !!remetenteEmail && remetenteEmail !== emailContaSmtp;
  const podeEnviar = destinatarios.length > 0 && assunto.trim().length > 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-dark/45 p-4"
      onClick={aoFechar}
    >
      <div
        className="flex max-h-[92vh] w-full max-w-lg flex-col rounded-xl bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between border-b border-dark/[.07] px-6 py-4">
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-dark">Enviar por email</h2>
            <p className="mt-0.5 truncate text-xs text-dark/70">
              Anexo: {doc.nome_original.replace(/\.docx$/i, ".pdf")}
            </p>
          </div>
          <button
            onClick={aoFechar}
            className="ml-3 rounded-lg p-1 text-dark/55 transition hover:bg-cinza hover:text-dark/88"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="min-h-0 flex-1 space-y-4 overflow-auto px-6 py-5">
          {isLoading ? (
            <div className="flex justify-center py-10">
              <Loader2 className="h-5 w-5 animate-spin text-navy/40" />
            </div>
          ) : (
            <>
              {padrao && !padrao.smtp_configurado && (
                <div className="flex items-start gap-2.5 rounded-lg bg-risco/10 px-3.5 py-3">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-risco" />
                  <p className="text-xs text-risco">
                    O SMTP ainda nao esta configurado. Preencha a aba Email em
                    Configuracoes antes de enviar.
                  </p>
                </div>
              )}

              {/* ---- remetente ---- */}
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="rotulo">Remetente — nome</label>
                  <input
                    className="campo"
                    placeholder="Escritorio Silva Advogados"
                    value={remetenteNome}
                    onChange={(e) => setRemetenteNome(e.target.value)}
                  />
                </div>
                <div>
                  <label className="rotulo">Remetente — email</label>
                  <input
                    type="email"
                    className="campo"
                    value={remetenteEmail}
                    onChange={(e) => setRemetenteEmail(e.target.value)}
                  />
                </div>
              </div>

              {remetenteAlterado && (
                <p className="rounded-lg bg-amber/10 px-3 py-2 text-xs text-amber">
                  Voce trocou o email do remetente. Gmail e Microsoft 365
                  costumam recusar ou reescrever um remetente diferente da conta
                  autenticada ({emailContaSmtp}) — funciona apenas se este
                  endereco for um alias verificado. As respostas virao para ele
                  de qualquer forma.
                </p>
              )}

              {/* ---- destinatarios ---- */}
              <div>
                <label className="rotulo">Destinatarios</label>
                <div className="flex flex-wrap items-center gap-1.5 rounded-lg border border-dark/10 bg-white p-2">
                  {destinatarios.map((email) => (
                    <span
                      key={email}
                      className="flex items-center gap-1.5 rounded-md bg-navy/10 px-2 py-1 text-xs text-navy"
                    >
                      {email}
                      <button
                        onClick={() =>
                          setDestinatarios(destinatarios.filter((d) => d !== email))
                        }
                        className="text-navy/50 transition hover:text-risco"
                        aria-label={`Remover ${email}`}
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </span>
                  ))}
                  <input
                    className="min-w-[160px] flex-1 border-0 px-1.5 py-1 text-sm outline-none
                               placeholder:text-dark/55"
                    placeholder={
                      destinatarios.length ? "Adicionar outro..." : "cliente@exemplo.com"
                    }
                    value={entrada}
                    onChange={(e) => setEntrada(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === "," || e.key === " ") {
                        e.preventDefault();
                        adicionar(entrada);
                      }
                      if (e.key === "Backspace" && !entrada && destinatarios.length) {
                        setDestinatarios(destinatarios.slice(0, -1));
                      }
                    }}
                    onBlur={() => entrada && adicionar(entrada)}
                  />
                </div>
                <p className="mt-1.5 text-xs text-dark/65">
                  Enter ou virgula adiciona. Ate 20 destinatarios.
                </p>
              </div>

              <div>
                <label className="rotulo">Assunto</label>
                <input
                  className="campo"
                  value={assunto}
                  onChange={(e) => setAssunto(e.target.value)}
                />
              </div>

              <div>
                <label className="rotulo">Mensagem</label>
                <textarea
                  className="campo resize-y"
                  rows={5}
                  value={mensagem}
                  onChange={(e) => setMensagem(e.target.value)}
                />
                <p className="mt-1.5 text-xs text-dark/65">
                  Vai dentro do template com a identidade do escritorio, junto
                  do codigo de autenticidade do documento.
                </p>
              </div>
            </>
          )}
        </div>

        <div className="flex justify-end gap-2 border-t border-dark/[.07] px-6 py-4">
          <button
            onClick={aoFechar}
            className="rounded-lg px-4 py-2.5 text-sm text-dark/80 transition hover:bg-cinza"
          >
            Cancelar
          </button>
          <button
            onClick={() => enviar.mutate()}
            disabled={!podeEnviar || enviar.isPending}
            className={cn("btn-primario")}
          >
            {enviar.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            Enviar
          </button>
        </div>
      </div>
    </div>
  );
}
