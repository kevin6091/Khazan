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
