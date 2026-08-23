package com.vardath.janus.v080;

import android.content.Intent;
import android.os.Bundle;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;

/** Compatibility trampoline for stale development shortcuts. The product surface is MainActivity. */
public final class HomeActivity extends AppCompatActivity {
    @Override protected void onCreate(@Nullable Bundle state){
        super.onCreate(state);
        startActivity(new Intent(this,MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP));
        finish();
    }
}
