import { redirect } from "next/navigation";

// Hoje ha um unico tenant. Quando houver varios, esta raiz vira a
// tela de escolha/identificacao do escritorio.
const TENANT_PADRAO = process.env.NEXT_PUBLIC_TENANT_PADRAO ?? "escritorio";

export default function Home() {
  redirect(`/${TENANT_PADRAO}/documentos`);
}
