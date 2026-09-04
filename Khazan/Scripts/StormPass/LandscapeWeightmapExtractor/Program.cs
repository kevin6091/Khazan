using System.Text.Json;
using System.Runtime.InteropServices;
using CUE4Parse.Compression;
using CUE4Parse.Encryption.Aes;
using CUE4Parse.FileProvider;
using CUE4Parse.UE4.Assets.Exports.Actor;
using CUE4Parse.UE4.Assets.Exports.Component.Landscape;
using CUE4Parse.UE4.Assets.Exports.Material;
using CUE4Parse.UE4.Assets.Exports.Texture;
using CUE4Parse.UE4.Objects.Core.Misc;
using CUE4Parse.UE4.Versions;
using CUE4Parse_Conversion.Dto;
using CUE4Parse_Conversion.Options;
using CUE4Parse_Conversion.Textures;
using Serilog;
using Serilog.Sinks.SystemConsole.Themes;
using SkiaSharp;

internal static class Program
{
    private sealed record FModelConfiguration(string GameDirectory, string AesKey);

    private sealed record LandscapeTarget(string PackagePath, string ActorName, string OutputName);

    private sealed record MaterialTarget(string FileName, string OutputName);

    private sealed record TextureParameterRecord(
        string MaterialName,
        string ParameterName,
        string ObjectPath,
        string ObjectName);

    private static readonly LandscapeTarget[] Targets =
    [
        new(
            "BBQ/Content/_Kazan_/Level/StormPass/StormPass_Landscape",
            "Landscape_mainfield",
            "StormPass_Landscape"),
        new(
            "BBQ/Content/_Kazan_/Level/StormPass/StormPass_Boss_Phase_2",
            "Landscape_0",
            "StormPass_Boss_Phase_2")
    ];

    private static readonly MaterialTarget[] MaterialTargets =
    [
        new("WLM_Stormpass.json", "WLM_Stormpass"),
        new("WLM_Stormpass_Phase2.json", "WLM_Stormpass_Phase2")
    ];

    private const string ParentMaterialPackage =
        "BBQ/Content/_Kazan_/Art/Terrain/Terrain_Material/Landscape_Material/WLM_Base_Terrain5_Inst";

    private static async Task<int> Main(string[] args)
    {
        Log.Logger = new LoggerConfiguration()
            .MinimumLevel.Information()
            .Filter.ByExcluding(logEvent =>
                logEvent.RenderMessage().Equals(
                    "File version is too new or too old",
                    StringComparison.Ordinal))
            .WriteTo.Console(theme: AnsiConsoleTheme.Literate)
            .CreateLogger();
        CUE4Parse.CUE4ParseLog.UseLogger(Log.Logger);

        var projectRoot = args.Length > 0
            ? Path.GetFullPath(args[0])
            : FindProjectRoot(AppContext.BaseDirectory);
        var outputRoot = args.Length > 1
            ? Path.GetFullPath(args[1])
            : Path.Combine(projectRoot, "Saved", "Extracted", "StormPass", "LandscapeWeightmaps");
        var materialJsonRoot = args.Length > 2
            ? Path.GetFullPath(args[2])
            : Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
                "Desktop",
                "카잔",
                "Exports",
                "BBQ",
                "Content",
                "_Kazan_",
                "Art",
                "Terrain",
                "Terrain_Material",
                "Landscape_Material");
        var surfaceOutputRoot = Path.Combine(
            projectRoot, "Saved", "Extracted", "StormPass", "LandscapeSurfaceTextures");
        Directory.CreateDirectory(outputRoot);
        Directory.CreateDirectory(surfaceOutputRoot);

        var configuration = ReadFModelConfiguration();
        var pakRoot = Path.Combine(configuration.GameDirectory, "Content", "Paks");
        if (!Directory.Exists(pakRoot))
            throw new DirectoryNotFoundException($"Game pak directory is unavailable: {pakRoot}");

        ZlibHelper.Initialize();
        OodleHelper.Initialize();
        var versions = new VersionContainer(EGame.GAME_UE4_27, ETexturePlatform.DesktopMobile);
        using var provider = new DefaultFileProvider(
            pakRoot,
            SearchOption.TopDirectoryOnly,
            true,
            versions);
        provider.Initialize();
        provider.SubmitKey(new FGuid(), new FAesKey(configuration.AesKey));
        provider.PostMount();

        var summaries = new List<object>();
        foreach (var target in Targets)
        {
            Log.Information("Loading {PackagePath}", target.PackagePath);
            var package = provider.LoadPackage(target.PackagePath);
            var landscapes = package.GetExports()
                .OfType<ALandscapeProxy>()
                .Where(actor => actor.Name.Equals(target.ActorName, StringComparison.Ordinal))
                .ToArray();
            if (landscapes.Length != 1)
                throw new InvalidOperationException(
                    $"Expected one {target.ActorName} export, found {landscapes.Length}");

            var outputDirectory = Path.Combine(outputRoot, target.OutputName);
            Directory.CreateDirectory(outputDirectory);
            using var dto = new LandscapeMeshDto(landscapes[0], ELandscapeFlags.Weightmap);
            if (dto.BitmapTextures is null || dto.BitmapTextures.Count == 0)
                throw new InvalidOperationException($"No Landscape weightmaps decoded for {target.OutputName}");

            var files = new List<object>();
            foreach (var (layerName, bitmap) in dto.BitmapTextures.OrderBy(item => item.Key))
            {
                var safeName = SanitizeFileName(layerName);
                var outputPath = Path.Combine(outputDirectory, safeName + ".png");
                using var encoded = bitmap.Encode(SKEncodedImageFormat.Png, 100);
                await File.WriteAllBytesAsync(outputPath, encoded.ToArray());
                files.Add(new
                {
                    layer_name = layerName,
                    path = outputPath,
                    width = bitmap.Width,
                    height = bitmap.Height,
                    bytes = new FileInfo(outputPath).Length,
                    statistics = GetGrayscaleStatistics(bitmap)
                });
                Log.Information(
                    "Decoded {Level}/{Layer} ({Width}x{Height})",
                    target.OutputName,
                    layerName,
                    bitmap.Width,
                    bitmap.Height);
            }

            summaries.Add(new
            {
                source_package = target.PackagePath,
                landscape_actor = target.ActorName,
                output_name = target.OutputName,
                component_count = landscapes[0].LandscapeComponents.Length,
                layer_count = files.Count,
                layers = files,
                layer_info_mappings = GetLayerInfoMappings(landscapes[0])
            });
        }

        var (materialSummaries, textureParameters) = ReadMaterialSources(materialJsonRoot);
        var (parentSummary, parentTextures) = ReadMaterialInstanceFromPackage(
            provider, ParentMaterialPackage);
        materialSummaries.Add(parentSummary);
        textureParameters.AddRange(parentTextures);
        var surfaceTextures = await ExtractSurfaceTextures(
            provider,
            versions,
            textureParameters,
            surfaceOutputRoot);

        var manifest = new
        {
            status = "passed",
            engine_version = "GAME_UE4_27",
            extraction_backend = "FModel-compatible CUE4Parse LandscapeMeshDto",
            source_game_directory = configuration.GameDirectory,
            output_root = outputRoot,
            landscapes = summaries,
            source_material_json_root = materialJsonRoot,
            source_materials = materialSummaries,
            surface_texture_output_root = surfaceOutputRoot,
            surface_texture_count = surfaceTextures.Count,
            surface_textures = surfaceTextures
        };
        var manifestPath = Path.Combine(outputRoot, "StormPass_LandscapeWeightmaps.json");
        await File.WriteAllTextAsync(
            manifestPath,
            JsonSerializer.Serialize(manifest, new JsonSerializerOptions { WriteIndented = true }) + Environment.NewLine);
        Console.WriteLine(manifestPath);
        return 0;
    }

    private static List<object> GetLayerInfoMappings(ALandscapeProxy landscape)
    {
        var mappings = new Dictionary<string, HashSet<string>>(StringComparer.Ordinal);
        foreach (var componentReference in landscape.LandscapeComponents)
        {
            var component = componentReference.Load<ULandscapeComponent>();
            if (component is null)
                throw new InvalidOperationException("A Landscape component reference could not be loaded");
            foreach (var allocation in component.GetWeightmapLayerAllocations())
            {
                var exportedLayerName = allocation.GetLayerName();
                var layerInfo = allocation.LayerInfo.Load<ULandscapeLayerInfoObject>();
                var materialLayerName = layerInfo?.LayerName.ToString() ?? exportedLayerName;
                if (!mappings.TryGetValue(exportedLayerName, out var materialNames))
                {
                    materialNames = new HashSet<string>(StringComparer.Ordinal);
                    mappings.Add(exportedLayerName, materialNames);
                }
                materialNames.Add(materialLayerName);
            }
        }

        return mappings
            .OrderBy(item => item.Key, StringComparer.Ordinal)
            .Select(item => (object)new
            {
                exported_layer_name = item.Key,
                material_layer_names = item.Value.OrderBy(value => value, StringComparer.Ordinal).ToArray()
            })
            .ToList();
    }

    private static (List<object> Summaries, List<TextureParameterRecord> Textures) ReadMaterialSources(
        string materialJsonRoot)
    {
        var summaries = new List<object>();
        var allTextures = new List<TextureParameterRecord>();
        foreach (var target in MaterialTargets)
        {
            var path = Path.Combine(materialJsonRoot, target.FileName);
            if (!File.Exists(path))
                throw new FileNotFoundException("Landscape material JSON is unavailable", path);
            using var document = JsonDocument.Parse(File.ReadAllText(path));
            var exports = document.RootElement;
            if (exports.ValueKind != JsonValueKind.Array || exports.GetArrayLength() != 1)
                throw new InvalidOperationException($"Expected one material export in {path}");
            var material = exports[0];
            var properties = material.GetProperty("Properties");
            var scalarParameters = ReadParameterRows(properties, "ScalarParameterValues");
            var vectorParameters = ReadParameterRows(properties, "VectorParameterValues");
            var textureParameters = new List<TextureParameterRecord>();
            if (properties.TryGetProperty("TextureParameterValues", out var textureValues))
            {
                foreach (var parameter in textureValues.EnumerateArray())
                {
                    var name = ParameterName(parameter);
                    var value = parameter.GetProperty("ParameterValue");
                    var objectPath = value.GetProperty("ObjectPath").GetString()
                        ?? throw new InvalidOperationException($"Texture parameter {name} has no ObjectPath");
                    var objectName = value.GetProperty("ObjectName").GetString()
                        ?? throw new InvalidOperationException($"Texture parameter {name} has no ObjectName");
                    objectName = TrimQuotedObjectName(objectName);
                    var record = new TextureParameterRecord(
                        target.OutputName,
                        name,
                        objectPath,
                        objectName);
                    textureParameters.Add(record);
                    allTextures.Add(record);
                }
            }

            string? parent = null;
            if (properties.TryGetProperty("Parent", out var parentValue) &&
                parentValue.TryGetProperty("ObjectPath", out var parentPath))
                parent = parentPath.GetString();
            var staticParameters = properties.TryGetProperty("StaticParameters", out var staticValue)
                ? staticValue.Clone()
                : (JsonElement?)null;
            var basePropertyOverrides = properties.TryGetProperty("BasePropertyOverrides", out var overrideValue)
                ? overrideValue.Clone()
                : (JsonElement?)null;
            summaries.Add(new
            {
                source_json = path,
                material_name = target.OutputName,
                parent,
                scalar_parameter_count = scalarParameters.Count,
                scalar_parameters = scalarParameters,
                vector_parameter_count = vectorParameters.Count,
                vector_parameters = vectorParameters,
                texture_parameter_count = textureParameters.Count,
                texture_parameters = textureParameters,
                static_parameters = staticParameters,
                base_property_overrides = basePropertyOverrides
            });
        }
        return (summaries, allTextures);
    }

    private static (object Summary, List<TextureParameterRecord> Textures) ReadMaterialInstanceFromPackage(
        DefaultFileProvider provider,
        string packagePath)
    {
        Log.Information("Loading inherited Landscape material {PackagePath}", packagePath);
        var package = provider.LoadPackage(packagePath);
        var instances = package.GetExports().OfType<UMaterialInstanceConstant>().ToArray();
        if (instances.Length != 1)
            throw new InvalidOperationException(
                $"Expected one material instance in {packagePath}, found {instances.Length}");
        var instance = instances[0];
        var scalarParameters = instance.ScalarParameterValues
            .OrderBy(parameter => parameter.Name, StringComparer.Ordinal)
            .Select(parameter => (object)new
            {
                name = parameter.Name,
                value = parameter.ParameterValue
            })
            .ToList();
        var vectorParameters = instance.VectorParameterValues
            .OrderBy(parameter => parameter.Name, StringComparer.Ordinal)
            .Select(parameter => (object)new
            {
                name = parameter.Name,
                value = parameter.ParameterValue?.ToString()
            })
            .ToList();
        var textureParameters = new List<TextureParameterRecord>();
        foreach (var parameter in instance.TextureParameterValues.OrderBy(
                     parameter => parameter.Name, StringComparer.Ordinal))
        {
            var texture = parameter.ParameterValue.Load<UTexture2D>();
            if (texture is null)
                throw new InvalidOperationException(
                    $"Inherited texture parameter {parameter.Name} could not be loaded");
            textureParameters.Add(new TextureParameterRecord(
                instance.Name,
                parameter.Name,
                texture.GetPathName(),
                texture.Name));
        }
        var switches = instance.StaticParameters?.StaticSwitchParameters
            .OrderBy(parameter => parameter.Name, StringComparer.Ordinal)
            .Select(parameter => new
            {
                name = parameter.Name,
                value = parameter.Value
            })
            .ToArray();
        var summary = new
        {
            source_package = packagePath,
            material_name = instance.Name,
            parent = instance.Parent?.GetPathName(),
            scalar_parameter_count = scalarParameters.Count,
            scalar_parameters = scalarParameters,
            vector_parameter_count = vectorParameters.Count,
            vector_parameters = vectorParameters,
            texture_parameter_count = textureParameters.Count,
            texture_parameters = textureParameters,
            static_switch_parameters = switches
        };
        return (summary, textureParameters);
    }

    private static List<object> ReadParameterRows(JsonElement properties, string propertyName)
    {
        var rows = new List<object>();
        if (!properties.TryGetProperty(propertyName, out var values))
            return rows;
        foreach (var parameter in values.EnumerateArray())
        {
            rows.Add(new
            {
                name = ParameterName(parameter),
                value = parameter.GetProperty("ParameterValue").Clone()
            });
        }
        return rows;
    }

    private static string ParameterName(JsonElement parameter)
    {
        return parameter
            .GetProperty("ParameterInfo")
            .GetProperty("Name")
            .GetString()
            ?? throw new InvalidOperationException("Material parameter name is empty");
    }

    private static string TrimQuotedObjectName(string value)
    {
        var firstQuote = value.IndexOf('\'');
        var lastQuote = value.LastIndexOf('\'');
        return firstQuote >= 0 && lastQuote > firstQuote
            ? value[(firstQuote + 1)..lastQuote]
            : value;
    }

    private static async Task<List<object>> ExtractSurfaceTextures(
        DefaultFileProvider provider,
        VersionContainer versions,
        IReadOnlyCollection<TextureParameterRecord> parameters,
        string outputRoot)
    {
        var files = new List<object>();
        var grouped = parameters
            .GroupBy(parameter => parameter.ObjectPath, StringComparer.Ordinal)
            .OrderBy(group => group.Key, StringComparer.Ordinal)
            .ToArray();
        var duplicateNames = grouped
            .GroupBy(group => group.First().ObjectName, StringComparer.OrdinalIgnoreCase)
            .Where(group => group.Count() > 1)
            .Select(group => group.Key)
            .ToHashSet(StringComparer.OrdinalIgnoreCase);

        foreach (var group in grouped)
        {
            var source = group.First();
            var dot = source.ObjectPath.LastIndexOf('.');
            var packagePath = dot >= 0 ? source.ObjectPath[..dot] : source.ObjectPath;
            Log.Information("Loading Landscape surface texture {PackagePath}", packagePath);
            var package = provider.LoadPackage(packagePath);
            var candidates = package.GetExports().OfType<UTexture2D>().ToArray();
            var texture = candidates.FirstOrDefault(candidate =>
                candidate.Name.Equals(source.ObjectName, StringComparison.Ordinal));
            texture ??= candidates.Length == 1 ? candidates[0] : null;
            if (texture is null)
                throw new InvalidOperationException(
                    $"Texture export {source.ObjectName} is unresolved in {packagePath}");
            var bitmap = texture.Decode(versions.Platform);
            if (bitmap is null)
                throw new InvalidOperationException($"Texture decode failed: {source.ObjectPath}");

            var fileStem = SanitizeFileName(source.ObjectName);
            if (duplicateNames.Contains(source.ObjectName))
                fileStem += "_" + SanitizeFileName(packagePath.Replace('/', '_'));
            var encoded = bitmap.Encode(ETextureFormat.Png, false, out var extension, 100);
            var outputPath = Path.Combine(outputRoot, fileStem + "." + extension);
            await File.WriteAllBytesAsync(outputPath, encoded);
            files.Add(new
            {
                source_object_path = source.ObjectPath,
                source_object_name = source.ObjectName,
                path = outputPath,
                width = bitmap.Width,
                height = bitmap.Height,
                bytes = new FileInfo(outputPath).Length,
                parameter_bindings = group
                    .OrderBy(item => item.MaterialName, StringComparer.Ordinal)
                    .ThenBy(item => item.ParameterName, StringComparer.Ordinal)
                    .Select(item => new
                    {
                        material_name = item.MaterialName,
                        parameter_name = item.ParameterName
                    })
                    .ToArray()
            });
            Log.Information(
                "Decoded surface texture {Texture} ({Width}x{Height})",
                source.ObjectName,
                bitmap.Width,
                bitmap.Height);
        }
        return files;
    }

    private static object? GetGrayscaleStatistics(SKBitmap bitmap)
    {
        if (bitmap.ColorType != SKColorType.Gray8)
            return null;
        var bytes = new byte[bitmap.ByteCount];
        Marshal.Copy(bitmap.GetPixels(), bytes, 0, bytes.Length);
        var minimum = byte.MaxValue;
        var maximum = byte.MinValue;
        long sum = 0;
        long nonzero = 0;
        for (var y = 0; y < bitmap.Height; y++)
        {
            var row = y * bitmap.RowBytes;
            for (var x = 0; x < bitmap.Width; x++)
            {
                var value = bytes[row + x];
                if (value < minimum) minimum = value;
                if (value > maximum) maximum = value;
                if (value != 0) nonzero++;
                sum += value;
            }
        }
        var pixelCount = (long)bitmap.Width * bitmap.Height;
        return new
        {
            minimum,
            maximum,
            nonzero_pixel_count = nonzero,
            nonzero_fraction = pixelCount == 0 ? 0.0 : nonzero / (double)pixelCount,
            mean = pixelCount == 0 ? 0.0 : sum / (double)pixelCount
        };
    }

    private static FModelConfiguration ReadFModelConfiguration()
    {
        var settingsPath = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "FModel",
            "AppSettings.json");
        using var document = JsonDocument.Parse(File.ReadAllText(settingsPath));
        var root = document.RootElement;
        var configuredGameDirectory = root.GetProperty("GameDirectory").GetString()
            ?? throw new InvalidOperationException("FModel GameDirectory is empty");
        if (!root.TryGetProperty("PerDirectory", out var perDirectory))
            throw new InvalidOperationException("FModel PerDirectory settings are absent");

        foreach (var entry in perDirectory.EnumerateObject())
        {
            var value = entry.Value;
            if (!value.TryGetProperty("GameDirectory", out var gameDirectoryValue))
                continue;
            var gameDirectory = gameDirectoryValue.GetString();
            if (!string.Equals(gameDirectory, configuredGameDirectory, StringComparison.OrdinalIgnoreCase))
                continue;
            if (!value.TryGetProperty("AesKeys", out var aesKeys) ||
                !aesKeys.TryGetProperty("mainKey", out var mainKeyValue))
                continue;
            var mainKey = mainKeyValue.GetString();
            if (!string.IsNullOrWhiteSpace(mainKey))
                return new FModelConfiguration(configuredGameDirectory, mainKey);
        }
        throw new InvalidOperationException("The active FModel AES key could not be resolved");
    }

    private static string FindProjectRoot(string start)
    {
        var directory = new DirectoryInfo(start);
        while (directory is not null)
        {
            if (directory.EnumerateFiles("*.uproject", SearchOption.TopDirectoryOnly).Any())
                return directory.FullName;
            directory = directory.Parent;
        }
        throw new DirectoryNotFoundException("Unable to locate the Unreal project root");
    }

    private static string SanitizeFileName(string value)
    {
        var invalid = Path.GetInvalidFileNameChars().ToHashSet();
        return new string(value.Select(character => invalid.Contains(character) ? '_' : character).ToArray());
    }
}
