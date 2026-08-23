package com.vardath.janus;

import android.content.Context;

import androidx.annotation.NonNull;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

/** One-shot fast retry for chat turns queued during transient Render/network gaps. */
public class JanusQueueRetryWorker extends Worker {
    public JanusQueueRetryWorker(@NonNull Context context, @NonNull WorkerParameters params) {
        super(context, params);
    }

    @NonNull @Override public Result doWork() {
        int before = JanusOfflineQueue.pendingCount(getApplicationContext());
        if (before <= 0) return Result.success();
        JanusOfflineQueue.flush(getApplicationContext());
        int after = JanusOfflineQueue.pendingCount(getApplicationContext());
        return after < before ? Result.success() : Result.success();
    }
}
