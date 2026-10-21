using DubStage.Models;

namespace DubStage.Data;

public class ProjectRepository
{
    private readonly string _baseDir;
    private readonly DubStageDatabase _database;

    public ProjectRepository()
    {
        _baseDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "DubStageStudio");
        Directory.CreateDirectory(_baseDir);

        var dbPath = Path.Combine(_baseDir, "dubstage_v1.db");
        _database = new DubStageDatabase(dbPath);
    }

    public async Task InitializeAsync()
    {
        await _database.InitializeAsync();
    }

    public string BaseDirectory => _baseDir;

    public string GetProjectDirectory(string projectId)
    {
        var dir = Path.Combine(_baseDir, "projects", projectId);
        Directory.CreateDirectory(dir);
        return dir;
    }

    public string GetModelsDirectory()
    {
        var dir = Path.Combine(_baseDir, "models");
        Directory.CreateDirectory(dir);
        return dir;
    }

    public string GetTakesDirectory(string projectId)
    {
        var dir = Path.Combine(GetProjectDirectory(projectId), "takes");
        Directory.CreateDirectory(dir);
        return dir;
    }

    public string GetExportsDirectory(string projectId)
    {
        var dir = Path.Combine(GetProjectDirectory(projectId), "exports");
        Directory.CreateDirectory(dir);
        return dir;
    }

    public Task<List<ProjectEntity>> GetAllProjectsAsync() => _database.GetAllProjectsAsync();
    public Task SaveProjectAsync(ProjectEntity project) => _database.InsertOrUpdateProjectAsync(project);
    public Task<List<ClipEntity>> GetClipsForProjectAsync(string projectId) => _database.GetClipsForProjectAsync(projectId);
    public Task ReplaceClipsForProjectAsync(string projectId, IEnumerable<ClipEntity> clips) => _database.ReplaceClipsForProjectAsync(projectId, clips);
    public Task UpdateClipAsync(ClipEntity clip) => _database.UpdateClipAsync(clip);
    public Task<List<TakeEntity>> GetTakesForClipAsync(string clipId) => _database.GetTakesForClipAsync(clipId);
    public Task SaveTakeAsync(TakeEntity take) => _database.InsertTakeAsync(take);
    public Task UpdateTakeAsync(TakeEntity take) => _database.UpdateTakeAsync(take);
    public Task DeleteTakeAsync(string takeId) => _database.DeleteTakeAsync(takeId);
}
