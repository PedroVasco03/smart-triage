import { Badge } from "@/components/ui/badge";
import { BAND_COLORS } from "@/lib/constants";

export function BandBadge({ band }: { band: string }) {
  return <Badge color={BAND_COLORS[band] ?? "#6B7F8C"}>{band}</Badge>;
}
