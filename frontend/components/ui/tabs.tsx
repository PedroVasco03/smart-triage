"use client";

import * as React from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "@/lib/utils";

export const Tabs = TabsPrimitive.Root;

export const TabsList = ({ className, ...p }: React.ComponentProps<typeof TabsPrimitive.List>) => (
  <TabsPrimitive.List className={cn("inline-flex flex-wrap gap-1 rounded-lg border border-line bg-white p-1", className)} {...p} />
);
export const TabsTrigger = ({ className, ...p }: React.ComponentProps<typeof TabsPrimitive.Trigger>) => (
  <TabsPrimitive.Trigger
    className={cn(
      "rounded-md px-3 py-1.5 text-sm font-medium text-muted transition-colors data-[state=active]:bg-brand data-[state=active]:text-white",
      className,
    )}
    {...p}
  />
);
export const TabsContent = ({ className, ...p }: React.ComponentProps<typeof TabsPrimitive.Content>) => (
  <TabsPrimitive.Content className={cn("mt-4", className)} {...p} />
);
