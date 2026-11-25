// Bangla digits for user-facing numbers and identifiers ("305/1" -> "৩০৫/১"). Data stays ASCII.
const BN = "০১২৩৪৫৬৭৮৯";
export const bnDigits = (v: string | number | null | undefined): string =>
  v == null ? "" : String(v).replace(/[0-9]/g, (d) => BN[Number(d)]);
