"use client";

import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { UploadCloud, Sparkles, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { ErrorState } from "@/components/layout/error-state";
import { ResultGallery } from "@/components/features/results/result-gallery";
import {
  tryOnCategoryOptions,
  type VirtualTryOnPathRequest,
  virtualTryOnPathRequestSchema
} from "@/lib/schemas";
import { useTryOnPathMutation, useTryOnUploadMutation } from "@/hooks/use-tryon";

type PathFormValues = VirtualTryOnPathRequest;

function PreviewThumb({ file }: { file: File | null }) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!file) {
      setObjectUrl(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setObjectUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  if (!file || !objectUrl) {
    return (
      <div className="flex h-40 items-center justify-center rounded-2xl border border-dashed border-border bg-muted/30 text-sm text-muted-foreground">
        No preview selected
      </div>
    );
  }

  return <img src={objectUrl} alt={file.name} className="h-40 w-full rounded-2xl object-cover" />;
}

export function TryOnForm() {
  const uploadMutation = useTryOnUploadMutation();
  const pathMutation = useTryOnPathMutation();
  const [personFile, setPersonFile] = useState<File | null>(null);
  const [garmentFile, setGarmentFile] = useState<File | null>(null);

  const form = useForm<PathFormValues>({
    resolver: zodResolver(virtualTryOnPathRequestSchema),
    defaultValues: {
      person_image_path: "",
      garment_image_path: "",
      category: "upper_body"
    },
    mode: "onBlur"
  });

  const result = uploadMutation.data ?? pathMutation.data;

  const helperNotes = useMemo(
    () => [
      "Upload mode is best for browser-native files.",
      "Path mode works when you already have local filesystem paths from the backend.",
      "Returned result paths are previewed through the same workspace-safe proxy used by the frontend."
    ],
    []
  );

  return (
    <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
      <Card className="border-white/70">
        <CardHeader>
          <Badge variant="outline" className="w-fit">
            Virtual try-on
          </Badge>
          <CardTitle className="font-display text-2xl">Match garments to a person image</CardTitle>
          <CardDescription>
            Use uploaded images or explicit local paths, matching the backend's two available workflows.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {uploadMutation.isError || pathMutation.isError ? (
            <div className="mb-4">
              <ErrorState
                description={uploadMutation.error?.message || pathMutation.error?.message || "The try-on request failed."}
                onRetry={() => pathMutation.mutate(form.getValues())}
              />
            </div>
          ) : null}

          <Tabs defaultValue="upload" className="space-y-4">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="upload">Upload mode</TabsTrigger>
              <TabsTrigger value="paths">Path mode</TabsTrigger>
            </TabsList>

            <TabsContent value="upload" className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-3">
                  <Label htmlFor="person_file">Person image</Label>
                  <Input
                    id="person_file"
                    type="file"
                    accept="image/*"
                    onChange={(event) => setPersonFile(event.target.files?.[0] ?? null)}
                  />
                  <PreviewThumb file={personFile} />
                </div>
                <div className="space-y-3">
                  <Label htmlFor="garment_file">Garment image</Label>
                  <Input
                    id="garment_file"
                    type="file"
                    accept="image/*"
                    onChange={(event) => setGarmentFile(event.target.files?.[0] ?? null)}
                  />
                  <PreviewThumb file={garmentFile} />
                </div>
              </div>

              <div className="space-y-2">
                <Label>Category</Label>
                <Select defaultValue="upper_body">
                  <SelectTrigger>
                    <SelectValue placeholder="Upper body" />
                  </SelectTrigger>
                  <SelectContent>
                    {tryOnCategoryOptions.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <Button
                className="w-full"
                disabled={uploadMutation.isPending || !personFile || !garmentFile}
                onClick={() => {
                  const formData = new FormData();
                  if (personFile) {
                    formData.append("person_image", personFile);
                  }
                  if (garmentFile) {
                    formData.append("garment_image", garmentFile);
                  }
                  formData.append("category", "upper_body");
                  uploadMutation.mutate(formData);
                }}
              >
                {uploadMutation.isPending ? <RefreshCw className="h-4 w-4 animate-spin" /> : <UploadCloud className="h-4 w-4" />}
                {uploadMutation.isPending ? "Running try-on..." : "Run try-on"}
              </Button>
            </TabsContent>

            <TabsContent value="paths" className="space-y-4">
              <form className="space-y-4" onSubmit={form.handleSubmit((values) => pathMutation.mutate(values))}>
                <div className="space-y-2">
                  <Label htmlFor="person_image_path">Person path</Label>
                  <Input id="person_image_path" {...form.register("person_image_path")} placeholder="uploads/persons/person.png" />
                  {form.formState.errors.person_image_path ? (
                    <p className="text-sm text-rose-600">{form.formState.errors.person_image_path.message}</p>
                  ) : null}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="garment_image_path">Garment path</Label>
                  <Input id="garment_image_path" {...form.register("garment_image_path")} placeholder="outputs/generated_clothes/cloth.png" />
                  {form.formState.errors.garment_image_path ? (
                    <p className="text-sm text-rose-600">{form.formState.errors.garment_image_path.message}</p>
                  ) : null}
                </div>
                <div className="space-y-2">
                  <Label>Category</Label>
                  <Select
                    value={form.watch("category")}
                    onValueChange={(value) => form.setValue("category", value as PathFormValues["category"], { shouldValidate: true })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Upper body" />
                    </SelectTrigger>
                    <SelectContent>
                      {tryOnCategoryOptions.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <Button type="submit" className="w-full" disabled={pathMutation.isPending}>
                  {pathMutation.isPending ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                  {pathMutation.isPending ? "Running try-on..." : "Run try-on from path"}
                </Button>
              </form>
            </TabsContent>
          </Tabs>

          <div className="mt-6 rounded-2xl border border-emerald-200 bg-emerald-50/60 p-4 text-sm leading-6 text-emerald-950">
            {helperNotes.map((note) => (
              <p key={note}>• {note}</p>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="space-y-6">
        {result ? (
          <ResultGallery
            title="Try-on output"
            description="The backend returns a local file path. We preview it through the frontend file route."
            items={[
              {
                id: "tryon-result",
                path: result.result_path,
                metadata: result.metadata
              }
            ]}
          />
        ) : (
          <Card className="border-dashed">
            <CardHeader>
              <CardTitle className="font-display text-2xl">No try-on result yet</CardTitle>
              <CardDescription>Submit either the upload form or the path form to render the final image here.</CardDescription>
            </CardHeader>
          </Card>
        )}
      </div>
    </div>
  );
}
