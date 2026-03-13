import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...values: Array<string | false | null | undefined>) {
  return twMerge(clsx(values));
}
