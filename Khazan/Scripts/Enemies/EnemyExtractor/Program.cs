using System.Text.Json;
using CUE4Parse.Compression;
using CUE4Parse.Encryption.Aes;
using CUE4Parse.FileProvider;
using CUE4Parse.UE4.Objects.Core.Misc;
using CUE4Parse.UE4.Versions;
using CUE4Parse.UE4.Assets.Exports.Texture;
using Serilog;
using CUE4Parse_Conversion;
using CUE4Parse_Conversion.Options;
using CUE4Parse_Conversion.Exporters;
using CUE4Parse.UE4.Assets.Exports.SkeletalMesh;
using CUE4Parse.UE4.Assets.Exports.StaticMesh;
using CUE4Parse.UE4.Assets.Exports.Animation;
using CUE4Parse.UE4.Assets.Exports.Material;

// Targeted extraction with the user's existing FModel provider settings.
// Keys are read locally and never written to reports or the console.
internal static class Program
{
    static async Task<int> Main(string[] args)
    {
        var output = Path.GetFullPath(args[1]);
        Directory.CreateDirectory(output);
        Log.Logger = new LoggerConfiguration().MinimumLevel.Error().WriteTo.Console().CreateLogger();
        CUE4Parse.CUE4ParseLog.UseLogger(Log.Logger);
        if (args[0] == "audio-api")
        {
            foreach (var assembly in new[]{typeof(DefaultFileProvider).Assembly,typeof(ExportSession).Assembly})
            foreach (var t in assembly.GetTypes().Where(t =>
                t.Name.Contains("AkMedia") || t.Name.Contains("AkAudioEvent") || t.Name.Contains("AkAssetData") ||
                t.Name.Contains("AkAudioBank") || t.Name.Contains("SoundDecoder") ||
                t.Name == "GameFile" || t.Name == "VfsEntry" || t.Name == "FPakEntry"))
            {
                Console.WriteLine(t.FullName);
                foreach (var f in t.GetFields()) Console.WriteLine(" FIELD " + f);
                foreach (var p in t.GetProperties()) Console.WriteLine(" PROPERTY " + p);
                foreach (var m in t.GetMethods(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.DeclaredOnly)) Console.WriteLine(" METHOD " + m);
            }
            return 0;
        }
        if (args[0] == "api")
        {
            var assembly = typeof(CUE4Parse_Conversion.Dto.LandscapeMeshDto).Assembly;
            foreach (var t in assembly.GetExportedTypes().Where(t => t.Namespace == "CUE4Parse_Conversion" || t.Name == "ConversionContext"))
            {
                Console.WriteLine("PUBLIC " + t.FullName);
                foreach (var p in t.GetProperties()) Console.WriteLine(p);
                foreach (var f in t.GetFields()) Console.WriteLine(f);
                foreach (var m in t.GetMethods(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.DeclaredOnly)) Console.WriteLine(m);
            }
            foreach (var t in assembly.GetTypes().Where(t => new[]{"ExportOptions", "ExporterBase", "ExportResult", "ExportContext", "Exporter", "ExportFile", "ExportService", "ELodFormat", "EAnimFormat"}.Contains(t.Name)))
            {
                Console.WriteLine(t.FullName);
                if (t.IsEnum) Console.WriteLine(string.Join(",", Enum.GetNames(t)));
                foreach (var c in t.GetConstructors()) Console.WriteLine(c);
                foreach (var m in t.GetMethods(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.DeclaredOnly)) Console.WriteLine(m);
                foreach (var f in t.GetFields()) Console.WriteLine(f);
                foreach (var p in t.GetProperties()) Console.WriteLine(p);
            }
            return 0;
        }
        using var settings = JsonDocument.Parse(File.ReadAllText(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "FModel", "AppSettings.json")));
        var gameDir = settings.RootElement.GetProperty("GameDirectory").GetString()!;
        string? key = null;
        foreach (var entry in settings.RootElement.GetProperty("PerDirectory").EnumerateObject())
            if (entry.Value.TryGetProperty("GameDirectory", out var dir) && dir.GetString() == gameDir)
                key = entry.Value.GetProperty("AesKeys").GetProperty("mainKey").GetString();
        if (string.IsNullOrWhiteSpace(key)) throw new InvalidOperationException("Active FModel key unavailable");
        ZlibHelper.Initialize(); OodleHelper.Initialize();
        CUE4Parse_Conversion.Textures.TextureDecoder.UseAssetRipperTextureDecoder = true;
        using var provider = new DefaultFileProvider(Path.Combine(gameDir, "Content", "Paks"), SearchOption.TopDirectoryOnly, true,
            new VersionContainer(EGame.GAME_UE4_27, ETexturePlatform.DesktopMobile));
        provider.Initialize(); provider.SubmitKey(new FGuid(), new FAesKey(key)); provider.PostMount();
        provider.LoadVirtualPaths();
        if (args[0] == "audio-files")
        {
            var paths=JsonSerializer.Deserialize<string[]>(File.ReadAllText(args[2]))!;
            var rows=new List<object>();
            foreach (var path in paths.Distinct(StringComparer.OrdinalIgnoreCase))
            {
                if (!provider.Files.TryGetValue(path,out var file))
                { rows.Add(new{source=path,status="missing"});continue; }
                var target=Path.GetFullPath(Path.Combine(output,path));
                if (!target.StartsWith(output+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase)) throw new Exception("Audio output path escaped task directory");
                Directory.CreateDirectory(Path.GetDirectoryName(target)!);
                var bytes=file.Read();
                await File.WriteAllBytesAsync(target,bytes);
                rows.Add(new{source=path,status="exported",target,bytes=bytes.Length,
                    archive=file is CUE4Parse.UE4.VirtualFileSystem.VfsEntry entry?entry.Vfs.Name:null,
                    sha256=Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(bytes)).ToLowerInvariant()});
            }
            await File.WriteAllTextAsync(Path.Combine(output,"AudioFileExtractionReport.json"),JsonSerializer.Serialize(rows,new JsonSerializerOptions{WriteIndented=true}));
            Console.WriteLine($"Audio extraction {rows.Count} records");
            return rows.Any(row=>JsonSerializer.Serialize(row).Contains("\"missing\""))?1:0;
        }
        if (args[0] == "audio-index")
        {
            var rows = provider.Files.Where(pair =>
                pair.Key.Contains("Wwise",StringComparison.OrdinalIgnoreCase) ||
                pair.Key.Contains("/Audio/",StringComparison.OrdinalIgnoreCase) ||
                pair.Key.Contains("/Sound/",StringComparison.OrdinalIgnoreCase) ||
                new[]{".wem",".bnk",".pck",".wav",".ogg"}.Any(ext => pair.Key.EndsWith(ext,StringComparison.OrdinalIgnoreCase)))
                .OrderBy(pair=>pair.Key).Select(pair=>new{
                    path=pair.Key, type=pair.Value.GetType().FullName,
                    archive=pair.Value is CUE4Parse.UE4.VirtualFileSystem.VfsEntry entry ? entry.Vfs.Name : null,
                    bytes=pair.Value.Size
                }).ToArray();
            await File.WriteAllTextAsync(Path.Combine(output,"AudioPackageIndex.json"),JsonSerializer.Serialize(rows,new JsonSerializerOptions{WriteIndented=true}));
            Console.WriteLine($"Audio index {rows.Length} files");
            return 0;
        }
        if (args[0] == "font-data")
        {
            // Cooked FontFace streaming data is a separate .ufont file, not an export's .uexp bulk.
            var paths = JsonSerializer.Deserialize<string[]>(File.ReadAllText(args[2]))!;
            var report = new List<object>();
            foreach (var path in paths.Distinct())
            {
                var keyPath = path + ".ufont";
                if (!provider.Files.TryGetValue(keyPath, out var file))
                { report.Add(new {source=keyPath,status="missing"}); continue; }
                var target = Path.Combine(output, Path.GetFileName(path) + ".ttf");
                var bytes = file.Read();
                await File.WriteAllBytesAsync(target, bytes);
                report.Add(new {source=keyPath,status="exported",target,bytes=bytes.Length});
            }
            await File.WriteAllTextAsync(Path.Combine(output,"FontDataReport.json"),JsonSerializer.Serialize(report,new JsonSerializerOptions {WriteIndented=true}));
            Console.WriteLine($"Targeted font data: {report.Count} records");
            return 0;
        }
        if (args[0] == "brush-geometry")
        {
            // Targeted original BSP topology: the normal cooked JSON writer
            // omits the vertex pool, so Model.Bounds cannot reproduce concave WEPs.
            var paths = JsonSerializer.Deserialize<string[]>(File.ReadAllText(args[2]))!;
            var flags = System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance;
            foreach (var path in paths.Distinct())
            {
                var package = path.Split('.')[0];
                if (package.Contains("..") || Path.IsPathRooted(package) || !(provider.Files.ContainsKey(package+".uasset") || provider.Files.ContainsKey(package+".umap"))) throw new Exception("Package is not in the mounted FModel snapshot");
                var rows = provider.LoadPackage(package).GetExports()
                    .Where(o => o.GetType().Name.Contains("Model") && o.GetType().Name != "UModelComponent")
                    .Select(o => new { o.Name, type=o.GetType().FullName,
                        fields=o.GetType().GetFields(flags).Where(f => new[]{"Verts", "Vertices", "Points", "Vectors", "Nodes", "Surfs", "Bounds"}.Contains(f.Name))
                            .ToDictionary(f => f.Name, f => f.GetValue(o)),
                        available_fields=o.GetType().GetFields(flags).Select(f => f.Name).ToArray() }).ToArray();
                var target = Path.Combine(output, Path.GetFileName(package)+"_BrushGeometry.json");
                await File.WriteAllTextAsync(target, Newtonsoft.Json.JsonConvert.SerializeObject(rows, Newtonsoft.Json.Formatting.Indented));
                Console.WriteLine($"Brush geometry {package}: {rows.Length} models");
            }
            return 0;
        }
        if (args[0] == "export" || args[0] == "raw")
        {
            var paths = JsonSerializer.Deserialize<string[]>(File.ReadAllText(args[2]))!;
            var session = new ExportSession { MaxDegreeOfParallelism=2 };
            foreach (var path in paths.Distinct(StringComparer.OrdinalIgnoreCase))
            {
                var packagePath=path.Split('.')[0];
                if (args[0] == "raw") session.Add(new RawDataExporter(provider.Files[packagePath + ".uasset"], provider));
                else foreach (var obj in provider.LoadPackage(packagePath).GetExports())
                    if (obj is USkeletalMesh or UStaticMesh or UTexture or UAnimationAsset or UMaterialInterface)
                        session.Add(obj);
            }
            var results=await session.RunAsync(output, new ExportOptions(meshFormat:EMeshFormat.ActorX,meshQuality:EMeshQuality.All,exportMaterials:false,exportMorphTargets:true,socketFormat:ESocketFormat.Socket));
            await File.WriteAllTextAsync(Path.Combine(output,"ExportReport.json"),JsonSerializer.Serialize(results.Select(r=>new{r.Success,r.ObjectPath,r.DiskFilePaths,error=r.Error?.Message}),new JsonSerializerOptions{WriteIndented=true}));
            Console.WriteLine($"Export results {results.Count}, failed {results.Count(r=>!r.Success)}");
            return results.Any(r=>!r.Success)?1:0;
        }
        if (args[0] == "index")
        {
            var terms = args.Skip(2).ToArray();
            var paths = provider.Files.Keys.Where(p => p.EndsWith(".uasset", StringComparison.OrdinalIgnoreCase) && terms.Any(t => p.Contains(t, StringComparison.OrdinalIgnoreCase))).Order().ToArray();
            await File.WriteAllTextAsync(Path.Combine(output, "TargetedPackageIndex.json"), JsonSerializer.Serialize(paths, new JsonSerializerOptions { WriteIndented=true }));
            Console.WriteLine($"Targeted index: {paths.Length} packages");
            return 0;
        }
        if (args[0] == "metadata")
        {
            var paths = JsonSerializer.Deserialize<string[]>(File.ReadAllText(args[2]))!;
            var report = new List<object>();
            foreach (var source in paths.Distinct())
            {
                try
                {
                    var packagePath = source.Split('.')[0];
                    if (packagePath.Contains("..") || Path.IsPathRooted(packagePath) || !provider.Files.ContainsKey(packagePath+".uasset")) throw new Exception("Package is not in the mounted FModel snapshot");
                    var target = Path.GetFullPath(Path.Combine(output, packagePath + ".json"));
                    Directory.CreateDirectory(Path.GetDirectoryName(target)!);
                    var exports = provider.LoadPackage(packagePath).GetExports().ToArray();
                    await File.WriteAllTextAsync(target, Newtonsoft.Json.JsonConvert.SerializeObject(exports, Newtonsoft.Json.Formatting.Indented));
                    report.Add(new {source=packagePath, target, exports=exports.Length, status="ok"});
                    Console.WriteLine($"Metadata {packagePath}: {exports.Length}");
                }
                catch (Exception e) { report.Add(new {source, status="failed", error=e.Message}); Console.WriteLine($"FAILED {source}: {e.Message}"); }
            }
            await File.WriteAllTextAsync(Path.Combine(output,"MetadataExtractionReport.json"),JsonSerializer.Serialize(report,new JsonSerializerOptions { WriteIndented=true }));
            return 0;
        }
        throw new Exception("Unknown mode");
    }
}
