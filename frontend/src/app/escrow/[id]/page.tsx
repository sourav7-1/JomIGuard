import EscrowDealClient from "./EscrowDealClient";

export default async function EscrowDealPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <EscrowDealClient id={id} />;
}
