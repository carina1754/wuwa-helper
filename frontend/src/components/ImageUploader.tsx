interface ImageUploaderProps {
  previewUrl: string | null;
  onFileSelected: (file: File) => void;
}

export function ImageUploader({ previewUrl, onFileSelected }: ImageUploaderProps) {
  return (
    <section className="rounded-md border border-dashed border-slate-300 bg-slate-50 p-4">
      <label className="block text-sm font-medium text-slate-700" htmlFor="screenshot-file">
        Screenshot
      </label>
      <input
        id="screenshot-file"
        type="file"
        accept="image/*"
        className="mt-2 block w-full text-sm text-slate-700"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onFileSelected(file);
        }}
      />
      {previewUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={previewUrl} alt="Uploaded screenshot preview" className="mt-4 max-h-80 w-full rounded-md object-contain" />
      ) : (
        <div className="mt-4 flex h-48 items-center justify-center rounded-md border border-slate-200 bg-white text-sm text-slate-500">
          Image preview appears here
        </div>
      )}
    </section>
  );
}
