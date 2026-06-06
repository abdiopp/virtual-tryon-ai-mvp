"use client";

import { useMemo } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { RefreshCw, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { generateClothesRequestSchema, type GenerateClothesRequest } from "@/lib/schemas";
import { defaultGenerationForm } from "@/lib/constants";
import { useGenerateClothesMutation } from "@/hooks/use-generate-clothes";
import { ErrorState } from "@/components/layout/error-state";
import { ResultGallery } from "@/components/features/results/result-gallery";

type FormValues = GenerateClothesRequest;

const categoryOptions = [
  { value: "hoodie", label: "Hoodie" },
  { value: "shirt", label: "Shirt" },
  { value: "jacket", label: "Jacket" },
  { value: "dress", label: "Dress" },
  { value: "pants", label: "Pants" }
];

export function GenerateForm() {
  const mutation = useGenerateClothesMutation();
  const form = useForm<FormValues>({
    resolver: zodResolver(generateClothesRequestSchema) as any,
    defaultValues: defaultGenerationForm as FormValues,
    mode: "onBlur"
  });

  const resultItems = mutation.data?.items ?? [];

  const helperNotes = useMemo(
    () => [
      "The backend caps count at 8.",
      "Non-CUDA devices may auto-adjust size, steps, and count.",
      "Turbo models ignore guidance scale and prefer 0.0."
    ],
    []
  );

  return (
    <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
      <Card className="border-white/70">
        <CardHeader>
          <Badge variant="outline" className="w-fit">
            Prompt studio
          </Badge>
          <CardTitle className="font-display text-2xl">Generate clothing assets</CardTitle>
          <CardDescription>
            Configure the existing SDXL-based backend with a polished interface and inline validation.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {mutation.isError ? (
            <div className="mb-4">
              <ErrorState description={mutation.error.message} onRetry={() => mutation.mutate(form.getValues())} />
            </div>
          ) : null}

          <form className="space-y-5" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
            <div className="space-y-2">
              <Label htmlFor="prompt">Prompt</Label>
              <Textarea id="prompt" {...form.register("prompt")} placeholder="Describe the garment you want to generate..." />
              {form.formState.errors.prompt ? (
                <p className="text-sm text-rose-600">{form.formState.errors.prompt.message}</p>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="category">Category</Label>
              <Select
                value={form.watch("category") ?? ""}
                onValueChange={(value) => form.setValue("category", value || undefined, { shouldValidate: true })}
              >
                <SelectTrigger id="category">
                  <SelectValue placeholder="Auto" />
                </SelectTrigger>
                <SelectContent>
                  {categoryOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="negative_prompt">Negative prompt</Label>
              <Textarea id="negative_prompt" {...form.register("negative_prompt")} placeholder="Optional custom negative prompt" />
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="count">Count</Label>
                <Input id="count" type="number" min={1} max={8} {...form.register("count")} />
                {form.formState.errors.count ? <p className="text-sm text-rose-600">{form.formState.errors.count.message}</p> : null}
              </div>
              <div className="space-y-2">
                <Label htmlFor="seed">Seed</Label>
                <Input id="seed" type="number" placeholder="Optional" {...form.register("seed")} />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="width">Width</Label>
                <Input id="width" type="number" min={256} max={1536} {...form.register("width")} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="height">Height</Label>
                <Input id="height" type="number" min={256} max={1536} {...form.register("height")} />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="guidance_scale">Guidance scale</Label>
                <Input id="guidance_scale" type="number" min={0} max={20} step={0.1} {...form.register("guidance_scale")} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="num_inference_steps">Steps</Label>
                <Input id="num_inference_steps" type="number" min={1} max={100} {...form.register("num_inference_steps")} />
              </div>
            </div>

            <div className="rounded-2xl border border-emerald-200 bg-emerald-50/60 p-4 text-sm leading-6 text-emerald-950">
              {helperNotes.map((note) => (
                <p key={note}>• {note}</p>
              ))}
            </div>

            <Button type="submit" disabled={mutation.isPending} className="w-full">
              {mutation.isPending ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              {mutation.isPending ? "Generating..." : "Generate garments"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <div className="space-y-6">
        {resultItems.length > 0 ? (
          <ResultGallery
            title="Generated results"
            description="Preview the returned filesystem paths through the local file proxy."
            items={resultItems}
          />
        ) : (
          <Card className="border-dashed">
            <CardHeader>
              <CardTitle className="font-display text-2xl">No results yet</CardTitle>
              <CardDescription>Run a generation request to see images, metadata, and copyable file paths here.</CardDescription>
            </CardHeader>
          </Card>
        )}
      </div>
    </div>
  );
}
