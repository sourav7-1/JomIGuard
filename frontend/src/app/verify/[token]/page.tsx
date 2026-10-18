import { IdentityFlow } from "@/components/IdentityFlow";

export default async function VerifyPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  return <IdentityFlow mode="seller" token={token} />;
}
