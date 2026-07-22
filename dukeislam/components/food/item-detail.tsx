"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useMediaQuery } from "@/hooks/use-media-query";
import type { NutritionInfo } from "@/lib/types";
import { NutritionLabel } from "./nutrition-label";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  info: NutritionInfo | null;
  itemName: string;
  restaurant: string;
}

export function ItemDetail({ open, onOpenChange, info, itemName, restaurant }: Props) {
  const isDesktop = useMediaQuery("(min-width: 768px)");

  const body = info ? (
    <NutritionLabel info={info} />
  ) : (
    <p className="rounded-xl bg-muted px-4 py-6 text-center text-sm text-muted-foreground">
      No nutrition data on file for this item yet. It&apos;s still verified halal on
      today&apos;s menu.
    </p>
  );

  if (isDesktop) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-h-[85vh] max-w-md gap-0 overflow-hidden p-0">
          <DialogHeader className="border-b px-6 py-4 text-left">
            <DialogTitle className="text-lg">{itemName}</DialogTitle>
            <DialogDescription>{restaurant} · Halal certified</DialogDescription>
          </DialogHeader>
          <ScrollArea className="max-h-[calc(85vh-5.5rem)]">
            <div className="p-6">{body}</div>
          </ScrollArea>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent className="max-h-[92dvh]">
        <DrawerHeader className="border-b pb-3 text-left">
          <DrawerTitle className="text-lg">{itemName}</DrawerTitle>
          <DrawerDescription>{restaurant} · Halal certified</DrawerDescription>
        </DrawerHeader>
        <div className="overflow-y-auto p-4 pb-8">{body}</div>
      </DrawerContent>
    </Drawer>
  );
}
