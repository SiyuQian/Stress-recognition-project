package com.szhu842.hr_ppg_monitor;

import android.app.ActivityManager;
import android.content.BroadcastReceiver;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.ServiceConnection;
import android.os.Bundle;
import android.os.IBinder;
import android.util.Log;
import android.widget.Button;
import android.widget.TextView;

import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;

import com.android.volley.AuthFailureError;
import com.android.volley.Request;
import com.android.volley.RequestQueue;
import com.android.volley.Response;
import com.android.volley.VolleyError;
import com.android.volley.toolbox.StringRequest;
import com.android.volley.toolbox.Volley;

import java.util.HashMap;
import java.util.Map;

import polar.com.sdk.api.PolarBleApi;

public class DataCollector extends AppCompatActivity {

    //    TextView textViewHR, textViewFW;
    private String TAG = "DataCollector";
    public PolarBleApi api;
    private String DEVICE_ID;
    private String device_name;
    private static DataCollector instance;

    private boolean update = false;

    public TextView deviceIDText;
    private TextView batteryText;
    private TextView PPGText;
    private Button recordDataBtn;
    private Button stopServiceBtn;

    private DataService dataService;
//    private Intent serviceIntent;

//    private boolean mBound = false;



    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_data_visualisation);
        DEVICE_ID = getIntent().getStringExtra("id");

        deviceIDText = findViewById(R.id.deviceIDText);
        batteryText = findViewById(R.id.batteryText);
        PPGText = findViewById(R.id.ppgText);
        recordDataBtn = findViewById(R.id.recordDataBtn);
        stopServiceBtn = findViewById(R.id.stopServiceBtn);

        startDataService();

        IntentFilter filter = new IntentFilter();
        filter.addAction("updatingState");
        registerReceiver(receiver, filter);


        recordDataBtn.setOnClickListener(v -> {
            if (DataCollector.this.recordDataBtn.getText().equals("Start Recording")) {

                Intent intent = new Intent("sendingState");
                intent.putExtra("sent", true);
                sendBroadcast(intent);
                DataCollector.this.recordDataBtn.setText("Stop Recording");

            } else {
                Intent intent = new Intent("sendingState");
                intent.putExtra("sent", false);
                sendBroadcast(intent);
                DataCollector.this.recordDataBtn.setText("Start Recording");
            }
        });

        stopServiceBtn.setOnClickListener(v-> {
            Intent intent = new Intent("turnoffService");
            sendBroadcast(intent);
        });

    }



    @Override
    protected void onStart() {
        super.onStart();
    }

    @Override
    public void onPause() {
        update = false;

        Intent pauseIntent = new Intent("onPause");
        sendBroadcast(pauseIntent);

        super.onPause();
    }

    @Override
    public void onResume() {
        update = true;

        Intent updateIntent = new Intent("requestUpdate");
        sendBroadcast(updateIntent);

        Intent resumeIntent = new Intent("onResume");
        sendBroadcast(resumeIntent);

//        if (dataService != null || dataService.api != null) {
//            dataService.api.foregroundEntered();
//        }

        super.onResume();
    }

    @Override
    public void onDestroy() {
        Log.d(TAG, "onDestroy: ");
        Intent broadcastIntent = new Intent();
        broadcastIntent.setAction("restartservice");
        broadcastIntent.setClass(this, Restarter.class);
        this.sendBroadcast(broadcastIntent);
        unregisterReceiver(receiver);
        super.onDestroy();
    }

    public DataCollector getInstance() {
        if (instance == null) {
            instance = new DataCollector();
        }
        return instance;
    }

    private void startDataService() {
        dataService = new DataService();

        Intent intent = new Intent(this, dataService.getClass());
//        intent.putExtra("id", DEVICE_ID);

        Log.d(TAG, "startDataService: ");
        if (!isMyServiceRunning(dataService.getClass())) {
            startService(intent);
        }
    }

    private void stopDataService(){
        Intent intent = new Intent(this,DataService.class);
        stopService(intent);
    }


    private boolean isMyServiceRunning(Class<?> serviceClass) {
        ActivityManager manager = (ActivityManager) getSystemService(Context.ACTIVITY_SERVICE);
        for (ActivityManager.RunningServiceInfo service : manager.getRunningServices(Integer.MAX_VALUE)) {
            if (serviceClass.getName().equals(service.service.getClassName())) {
                Log.d("isMyServiceRunning?", true + "");
                return true;
            }
        }
        Log.d("isMyServiceRunning?", false + "");
        return false;
    }

    private final BroadcastReceiver receiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            String action = intent.getAction();
            if (update) {
                if (action.equals("updatingState")) {
                    if (intent.getStringExtra("name") != null) {
                        deviceIDText.setText("ID: " + intent.getStringExtra("name"));
                    }
                    if (intent.getStringExtra("battery") != null) {
                        batteryText.setText("Battery: " + intent.getStringExtra("battery") + "%");
                    }
                    if (intent.getStringExtra("ppg") != null) {
                        PPGText.setText("PPG: " + intent.getStringExtra("ppg"));
                    }
                    if (intent.getStringExtra("buttonState") != null) {
                        if (intent.getStringExtra("buttonState").equals("true")) {
                            recordDataBtn.setText("Stop Recording");
                        } else {
                            recordDataBtn.setText("Start Recording");
                        }

                    }
                }
            }
        }
    };

//    // Monitors the state of the connection to the service.
//    private final ServiceConnection mServiceConnection = new ServiceConnection() {
//
//        @Override
//        public void onServiceConnected(ComponentName name, IBinder service) {
//            DataService.LocalBinder binder = (DataService.LocalBinder) service;
//            dataService = binder.getService();
//            mBound = true;
//        }
//
//        @Override
//        public void onServiceDisconnected(ComponentName name) {
//            dataService = null;
//            mBound = false;
//        }
//    };

}

