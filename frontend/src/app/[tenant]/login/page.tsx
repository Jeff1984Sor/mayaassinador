"use client";

import { useMutation } from "@tanstack/react-query";
import { Loader2, PenLine } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { z } from "zod";

import { api, mensagemErro } from "@/lib/api";
import { useAuth } from "@/store/auth";

const schema = z.object({
  email: z.string().email("Email invalido"),
  senha: z.string().min(1, "Informe a senha"),
});

export default function LoginPage() {
  const { tenant } = useParams<{ tenant: string }>();
  const router = useRouter();
  const { entrar, token, hidratado } = useAuth();

  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erros, setErros] = useState<Record<string, string>>({});

  // ja logado? nao faz sentido ver o login
  useEffect(() => {
    if (hidratado && token) router.replace(`/${tenant}/documentos`);
  }, [hidratado, token, tenant, router]);

  const login = useMutation({
    mutationFn: async () => {
      const { data } = await api.post("/api/auth/login", { email, senha });
      return data;
    },
    onSuccess: (data) => {
      entrar(data.access_token, data.usuario);
      toast.success(`Bem-vindo, ${data.usuario.nome.split(" ")[0]}!`);
      router.replace(`/${tenant}/documentos`);
    },
    onError: (e) => toast.error(mensagemErro(e, "Nao foi possivel entrar")),
  });

  function submeter(e: React.FormEvent) {
    e.preventDefault();
    const r = schema.safeParse({ email, senha });
    if (!r.success) {
      setErros(
        Object.fromEntries(
          r.error.issues.map((i) => [String(i.path[0]), i.message]),
        ),
      );
      return;
    }
    setErros({});
    login.mutate();
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-cinza px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-navy">
            <PenLine className="h-7 w-7 text-white" strokeWidth={2.2} />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-navy">
            MayaAssinador
          </h1>
          <p className="mt-1 text-sm text-dark/55">
            Documentos timbrados, rubricados e assinados
          </p>
        </div>

        <form onSubmit={submeter} className="cartao space-y-4 p-6">
          <div>
            <label htmlFor="email" className="rotulo">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              className="campo"
              placeholder="voce@escritorio.com.br"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            {erros.email && (
              <p className="mt-1.5 text-xs text-risco">{erros.email}</p>
            )}
          </div>

          <div>
            <label htmlFor="senha" className="rotulo">
              Senha
            </label>
            <input
              id="senha"
              type="password"
              autoComplete="current-password"
              className="campo"
              placeholder="••••••••"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
            />
            {erros.senha && (
              <p className="mt-1.5 text-xs text-risco">{erros.senha}</p>
            )}
          </div>

          <button
            type="submit"
            className="btn-primario w-full"
            disabled={login.isPending}
          >
            {login.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            {login.isPending ? "Entrando..." : "Entrar"}
          </button>
        </form>

        <p className="mt-6 text-center text-xs text-dark/40">
          MayaCorp · {new Date().getFullYear()}
        </p>
      </div>
    </main>
  );
}
