using Microsoft.Data.Sqlite;
using DubStage.Models;

namespace DubStage.Data;

public class DubStageDatabase
{
    private readonly string _dbPath;

    public DubStageDatabase(string dbPath)
    {
        _dbPath = dbPath;
    }

    public async Task InitializeAsync()
    {
        using var connection = new SqliteConnection($"Data Source={_dbPath}");
        await connection.OpenAsync();

        var tableCmd = connection.CreateCommand();
        tableCmd.CommandText = @"
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                video_path TEXT NOT NULL,
                video_duration_ms INTEGER NOT NULL,
                video_width INTEGER NOT NULL,
                video_height INTEGER NOT NULL,
                sample_rate INTEGER NOT NULL,
                channels INTEGER NOT NULL,
                original_wav_path TEXT,
                vocals_wav_path TEXT,
                backing_wav_path TEXT,
                model_checksum TEXT,
                status TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS clips (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                clip_index INTEGER NOT NULL,
                start_ms INTEGER NOT NULL,
                end_ms INTEGER NOT NULL,
                speaker_name TEXT NOT NULL,
                script_text TEXT NOT NULL,
                active_take_id TEXT,
                is_muted INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS takes (
                id TEXT PRIMARY KEY,
                clip_id TEXT NOT NULL,
                take_number INTEGER NOT NULL,
                audio_file_path TEXT NOT NULL,
                duration_ms INTEGER NOT NULL,
                gain_db REAL NOT NULL,
                time_offset_ms INTEGER NOT NULL,
                noise_gate_threshold_db REAL NOT NULL,
                recorded_at INTEGER NOT NULL,
                FOREIGN KEY (clip_id) REFERENCES clips(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_clips_project_id ON clips(project_id);
            CREATE INDEX IF NOT EXISTS idx_takes_clip_id ON takes(clip_id);
        ";
        await tableCmd.ExecuteNonQueryAsync();
    }

    public async Task<List<ProjectEntity>> GetAllProjectsAsync()
    {
        var list = new List<ProjectEntity>();
        using var connection = new SqliteConnection($"Data Source={_dbPath}");
        await connection.OpenAsync();

        using var cmd = connection.CreateCommand();
        cmd.CommandText = "SELECT id, title, video_path, video_duration_ms, video_width, video_height, sample_rate, channels, original_wav_path, vocals_wav_path, backing_wav_path, model_checksum, status, created_at, updated_at FROM projects ORDER BY updated_at DESC";
        using var reader = await cmd.ExecuteReaderAsync();
        while (await reader.ReadAsync())
        {
            list.Add(new ProjectEntity
            {
                Id = reader.GetString(0),
                Title = reader.GetString(1),
                VideoPath = reader.GetString(2),
                VideoDurationMs = reader.GetInt64(3),
                VideoWidth = reader.GetInt32(4),
                VideoHeight = reader.GetInt32(5),
                SampleRate = reader.GetInt32(6),
                Channels = reader.GetInt32(7),
                OriginalWavPath = reader.IsDBNull(8) ? null : reader.GetString(8),
                VocalsWavPath = reader.IsDBNull(9) ? null : reader.GetString(9),
                BackingWavPath = reader.IsDBNull(10) ? null : reader.GetString(10),
                ModelChecksum = reader.IsDBNull(11) ? null : reader.GetString(11),
                Status = reader.GetString(12),
                CreatedAt = reader.GetInt64(13),
                UpdatedAt = reader.GetInt64(14)
            });
        }
        return list;
    }

    public async Task InsertOrUpdateProjectAsync(ProjectEntity project)
    {
        using var connection = new SqliteConnection($"Data Source={_dbPath}");
        await connection.OpenAsync();

        using var cmd = connection.CreateCommand();
        cmd.CommandText = @"
            INSERT INTO projects (id, title, video_path, video_duration_ms, video_width, video_height, sample_rate, channels, original_wav_path, vocals_wav_path, backing_wav_path, model_checksum, status, created_at, updated_at)
            VALUES (@id, @title, @video_path, @video_duration_ms, @video_width, @video_height, @sample_rate, @channels, @original_wav_path, @vocals_wav_path, @backing_wav_path, @model_checksum, @status, @created_at, @updated_at)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                video_path = excluded.video_path,
                video_duration_ms = excluded.video_duration_ms,
                video_width = excluded.video_width,
                video_height = excluded.video_height,
                sample_rate = excluded.sample_rate,
                channels = excluded.channels,
                original_wav_path = excluded.original_wav_path,
                vocals_wav_path = excluded.vocals_wav_path,
                backing_wav_path = excluded.backing_wav_path,
                model_checksum = excluded.model_checksum,
                status = excluded.status,
                updated_at = excluded.updated_at;
        ";
        cmd.Parameters.AddWithValue("@id", project.Id);
        cmd.Parameters.AddWithValue("@title", project.Title);
        cmd.Parameters.AddWithValue("@video_path", project.VideoPath);
        cmd.Parameters.AddWithValue("@video_duration_ms", project.VideoDurationMs);
        cmd.Parameters.AddWithValue("@video_width", project.VideoWidth);
        cmd.Parameters.AddWithValue("@video_height", project.VideoHeight);
        cmd.Parameters.AddWithValue("@sample_rate", project.SampleRate);
        cmd.Parameters.AddWithValue("@channels", project.Channels);
        cmd.Parameters.AddWithValue("@original_wav_path", (object?)project.OriginalWavPath ?? DBNull.Value);
        cmd.Parameters.AddWithValue("@vocals_wav_path", (object?)project.VocalsWavPath ?? DBNull.Value);
        cmd.Parameters.AddWithValue("@backing_wav_path", (object?)project.BackingWavPath ?? DBNull.Value);
        cmd.Parameters.AddWithValue("@model_checksum", (object?)project.ModelChecksum ?? DBNull.Value);
        cmd.Parameters.AddWithValue("@status", project.Status);
        cmd.Parameters.AddWithValue("@created_at", project.CreatedAt);
        cmd.Parameters.AddWithValue("@updated_at", DateTimeOffset.UtcNow.ToUnixTimeMilliseconds());

        await cmd.ExecuteNonQueryAsync();
    }

    public async Task<List<ClipEntity>> GetClipsForProjectAsync(string projectId)
    {
        var list = new List<ClipEntity>();
        using var connection = new SqliteConnection($"Data Source={_dbPath}");
        await connection.OpenAsync();

        using var cmd = connection.CreateCommand();
        cmd.CommandText = "SELECT id, project_id, clip_index, start_ms, end_ms, speaker_name, script_text, active_take_id, is_muted, created_at FROM clips WHERE project_id = @proj_id ORDER BY clip_index ASC";
        cmd.Parameters.AddWithValue("@proj_id", projectId);

        using var reader = await cmd.ExecuteReaderAsync();
        while (await reader.ReadAsync())
        {
            list.Add(new ClipEntity
            {
                Id = reader.GetString(0),
                ProjectId = reader.GetString(1),
                ClipIndex = reader.GetInt32(2),
                StartMs = reader.GetInt64(3),
                EndMs = reader.GetInt64(4),
                SpeakerName = reader.GetString(5),
                ScriptText = reader.GetString(6),
                ActiveTakeId = reader.IsDBNull(7) ? null : reader.GetString(7),
                IsMuted = reader.GetInt32(8) == 1,
                CreatedAt = reader.GetInt64(9)
            });
        }
        return list;
    }

    public async Task ReplaceClipsForProjectAsync(string projectId, IEnumerable<ClipEntity> clips)
    {
        using var connection = new SqliteConnection($"Data Source={_dbPath}");
        await connection.OpenAsync();
        using var tx = connection.BeginTransaction();

        using var deleteCmd = connection.CreateCommand();
        deleteCmd.Transaction = tx;
        deleteCmd.CommandText = "DELETE FROM clips WHERE project_id = @pid";
        deleteCmd.Parameters.AddWithValue("@pid", projectId);
        await deleteCmd.ExecuteNonQueryAsync();

        foreach (var c in clips)
        {
            using var cmd = connection.CreateCommand();
            cmd.Transaction = tx;
            cmd.CommandText = @"
                INSERT INTO clips (id, project_id, clip_index, start_ms, end_ms, speaker_name, script_text, active_take_id, is_muted, created_at)
                VALUES (@id, @project_id, @clip_index, @start_ms, @end_ms, @speaker_name, @script_text, @active_take_id, @is_muted, @created_at)
            ";
            cmd.Parameters.AddWithValue("@id", c.Id);
            cmd.Parameters.AddWithValue("@project_id", projectId);
            cmd.Parameters.AddWithValue("@clip_index", c.ClipIndex);
            cmd.Parameters.AddWithValue("@start_ms", c.StartMs);
            cmd.Parameters.AddWithValue("@end_ms", c.EndMs);
            cmd.Parameters.AddWithValue("@speaker_name", c.SpeakerName);
            cmd.Parameters.AddWithValue("@script_text", c.ScriptText);
            cmd.Parameters.AddWithValue("@active_take_id", (object?)c.ActiveTakeId ?? DBNull.Value);
            cmd.Parameters.AddWithValue("@is_muted", c.IsMuted ? 1 : 0);
            cmd.Parameters.AddWithValue("@created_at", c.CreatedAt);
            await cmd.ExecuteNonQueryAsync();
        }

        tx.Commit();
    }

    public async Task UpdateClipAsync(ClipEntity clip)
    {
        using var connection = new SqliteConnection($"Data Source={_dbPath}");
        await connection.OpenAsync();

        using var cmd = connection.CreateCommand();
        cmd.CommandText = @"
            UPDATE clips SET
                clip_index = @clip_index,
                start_ms = @start_ms,
                end_ms = @end_ms,
                speaker_name = @speaker_name,
                script_text = @script_text,
                active_take_id = @active_take_id,
                is_muted = @is_muted
            WHERE id = @id
        ";
        cmd.Parameters.AddWithValue("@id", clip.Id);
        cmd.Parameters.AddWithValue("@clip_index", clip.ClipIndex);
        cmd.Parameters.AddWithValue("@start_ms", clip.StartMs);
        cmd.Parameters.AddWithValue("@end_ms", clip.EndMs);
        cmd.Parameters.AddWithValue("@speaker_name", clip.SpeakerName);
        cmd.Parameters.AddWithValue("@script_text", clip.ScriptText);
        cmd.Parameters.AddWithValue("@active_take_id", (object?)clip.ActiveTakeId ?? DBNull.Value);
        cmd.Parameters.AddWithValue("@is_muted", clip.IsMuted ? 1 : 0);
        await cmd.ExecuteNonQueryAsync();
    }

    public async Task<List<TakeEntity>> GetTakesForClipAsync(string clipId)
    {
        var list = new List<TakeEntity>();
        using var connection = new SqliteConnection($"Data Source={_dbPath}");
        await connection.OpenAsync();

        using var cmd = connection.CreateCommand();
        cmd.CommandText = "SELECT id, clip_id, take_number, audio_file_path, duration_ms, gain_db, time_offset_ms, noise_gate_threshold_db, recorded_at FROM takes WHERE clip_id = @cid ORDER BY take_number ASC";
        cmd.Parameters.AddWithValue("@cid", clipId);

        using var reader = await cmd.ExecuteReaderAsync();
        while (await reader.ReadAsync())
        {
            list.Add(new TakeEntity
            {
                Id = reader.GetString(0),
                ClipId = reader.GetString(1),
                TakeNumber = reader.GetInt32(2),
                AudioFilePath = reader.GetString(3),
                DurationMs = reader.GetInt64(4),
                GainDb = reader.GetFloat(5),
                TimeOffsetMs = reader.GetInt64(6),
                NoiseGateThresholdDb = reader.GetFloat(7),
                RecordedAt = reader.GetInt64(8)
            });
        }
        return list;
    }

    public async Task InsertTakeAsync(TakeEntity take)
    {
        using var connection = new SqliteConnection($"Data Source={_dbPath}");
        await connection.OpenAsync();

        using var cmd = connection.CreateCommand();
        cmd.CommandText = @"
            INSERT INTO takes (id, clip_id, take_number, audio_file_path, duration_ms, gain_db, time_offset_ms, noise_gate_threshold_db, recorded_at)
            VALUES (@id, @clip_id, @take_number, @audio_file_path, @duration_ms, @gain_db, @time_offset_ms, @noise_gate_threshold_db, @recorded_at)
        ";
        cmd.Parameters.AddWithValue("@id", take.Id);
        cmd.Parameters.AddWithValue("@clip_id", take.ClipId);
        cmd.Parameters.AddWithValue("@take_number", take.TakeNumber);
        cmd.Parameters.AddWithValue("@audio_file_path", take.AudioFilePath);
        cmd.Parameters.AddWithValue("@duration_ms", take.DurationMs);
        cmd.Parameters.AddWithValue("@gain_db", take.GainDb);
        cmd.Parameters.AddWithValue("@time_offset_ms", take.TimeOffsetMs);
        cmd.Parameters.AddWithValue("@noise_gate_threshold_db", take.NoiseGateThresholdDb);
        cmd.Parameters.AddWithValue("@recorded_at", take.RecordedAt);

        await cmd.ExecuteNonQueryAsync();
    }

    public async Task UpdateTakeAsync(TakeEntity take)
    {
        using var connection = new SqliteConnection($"Data Source={_dbPath}");
        await connection.OpenAsync();

        using var cmd = connection.CreateCommand();
        cmd.CommandText = @"
            UPDATE takes SET
                gain_db = @gain_db,
                time_offset_ms = @time_offset_ms,
                noise_gate_threshold_db = @noise_gate_threshold_db
            WHERE id = @id
        ";
        cmd.Parameters.AddWithValue("@id", take.Id);
        cmd.Parameters.AddWithValue("@gain_db", take.GainDb);
        cmd.Parameters.AddWithValue("@time_offset_ms", take.TimeOffsetMs);
        cmd.Parameters.AddWithValue("@noise_gate_threshold_db", take.NoiseGateThresholdDb);

        await cmd.ExecuteNonQueryAsync();
    }

    public async Task DeleteTakeAsync(string takeId)
    {
        using var connection = new SqliteConnection($"Data Source={_dbPath}");
        await connection.OpenAsync();

        using var cmd = connection.CreateCommand();
        cmd.CommandText = "DELETE FROM takes WHERE id = @id";
        cmd.Parameters.AddWithValue("@id", takeId);
        await cmd.ExecuteNonQueryAsync();
    }
}
