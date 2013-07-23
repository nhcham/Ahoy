package org.nhcham.ahoy;

import android.app.*;
import android.content.*;
import android.net.wifi.*;
import android.net.wifi.WifiManager.*;
import android.os.*;
import android.os.PowerManager;
import android.os.PowerManager.WakeLock;
import android.text.TextUtils;
import android.util.*;
import android.widget.*;
import java.io.BufferedInputStream;
import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.IOException;
import java.lang.*;
import java.security.SecureRandom;
import java.text.DateFormat;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.Calendar;
import java.util.concurrent.*;
import java.util.zip.GZIPInputStream;
import org.nhcham.ahoy.ApMessageFilter;
import org.nhcham.ahoy.WifiManagerExtended;

public class AhoyService extends Service {

    final static String TAG = "AhoyService";
    
    public static ApMessageFilter messageFilter = null;
    
    // after 5 minutes, a message is considered gone ( = no more active)
    final static long ACTIVE_TIMEOUT = 5 * 60;

    // if a message re-appears after 60 minutes of absence, a new
    // notification is shown for the message
    final static long RE_NOTIFY_TIMEOUT = 60 * 60;

    Thread serviceThread = null;
    IBinder binder = new LocalBinder();
    
    private enum ServiceCommand {
        NONE, SHUTDOWN, NEW_BROADCAST, STOP_BROADCAST, QUERY_STATE, 
        GOT_SCAN_RESULTS, PERFORM_SCAN
    }
    
    private class ServiceCommandWithOption {
        public final ServiceCommand command;
        public final Object option;
        
        public ServiceCommandWithOption(ServiceCommand _command, Object _option)
        {
            command = _command;
            option = _option;
        }

        public ServiceCommandWithOption(ServiceCommand _command)
        {
            command = _command;
            option = null;
        }
    }
    
    LinkedBlockingQueue<ServiceCommandWithOption> commandQueue = new LinkedBlockingQueue<ServiceCommandWithOption>();
    
    @Override
    public IBinder onBind(Intent intent) {
        return binder;
    }
    
    public class LocalBinder extends Binder {
        public AhoyService getServerInstance() {
            return AhoyService.this;
        }
    }
    
    public static Thread performOnBackgroundThread(final Runnable runnable) {
//         Log.d(TAG, "Now launching service thread...");
        final Thread t = new Thread() {
            @Override
            public void run() {
                try {
                    runnable.run();
                } finally {
                }
            }
        };
        t.start();
        return t;
    }        
    
    private class WifiScanReceiver extends BroadcastReceiver 
    {
        AhoyService ahoyService;

        public WifiScanReceiver(AhoyService _ahoyService)
        {
            super();
            ahoyService = _ahoyService;
        }

        @Override
        public void onReceive(Context c, Intent intent) 
        {
            ahoyService.gotScanResults();
        }
    }

    private class ServiceThread implements Runnable {
    
        final static String TAG = "AhoyServiceThread";
        
        final AhoyService service;
        WifiManagerExtended wifiManagerEx;
        WifiLock wifiLock = null;
        WifiScanReceiver scanReceiver;
        NotificationManager notificationManager;
        PowerManager powerManager;
        WakeLock wakeLock;
        SecureRandom secureRandom;
        
        String desiredBroadcastMessage = null;
        HashMap<String, HashMap<String, Long> > messageHash = new HashMap<String, HashMap<String, Long> >();
        boolean showSpinner = false;
        
        boolean originalWifiEnabled = false;
        boolean originalWifiApEnabled = false;
        WifiConfiguration originalWifiConfiguration = null;

        ServiceThread(AhoyService _service)
        {
            service = _service;
            wifiManagerEx = new WifiManagerExtended(_service);
            scanReceiver = new WifiScanReceiver(_service);
            notificationManager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
            powerManager = (PowerManager) getSystemService(Context.POWER_SERVICE);
            wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "AhoyService");
            secureRandom = new SecureRandom();
            messageFilter = new ApMessageFilter(_service);
        }
        
        public void _receivedScanResults()
        {
//             Log.d(TAG, "--------------------------GOT NEW SCAN RESULTS------------------------");
            List<ScanResult> results = wifiManagerEx.getScanResults();
            if (results != null)
            {
                List<String> notificationMessages = new ArrayList<String>();
                synchronized(messageHash) 
                {
                    final long currentTime = System.currentTimeMillis();
                        
                    // also, re-set counts to 0
                    for (String message : messageHash.keySet())
                    {
                        messageHash.get(message).put("count", new Long(0));
                        messageHash.get(message).put("level", new Long(-1000));
                    }
                        
                    Intent intent = new Intent("AhoyActivityUpdate");
                    for (ScanResult result: results) 
                    {
                        final String message = messageFilter.ssidToMessage(result.SSID);
                        if (message != null)
                        {
//                             Log.d(TAG, String.format("Caught a message: %s", message));
                            boolean showNotification = false;
                            
                            if (!messageHash.containsKey(message))
                            {
                                HashMap<String, Long> values = new HashMap<String, Long>();
                                values.put("firstSeen", currentTime);
                                values.put("count", new Long(1));
                                values.put("level", new Long(result.level));
                                values.put("index", new Long(messageHash.size()));
                                messageHash.put(message, values);
                                showNotification = true;
                            }
                            else
                                messageHash.get(message).put("count", messageHash.get(message).get("count") + 1);
                                
                            if (messageHash.get(message).containsKey("lastSeen"))
                            {
                                long previouslyLastSeen = messageHash.get(message).get("lastSeen");
                                if (currentTime - previouslyLastSeen >= RE_NOTIFY_TIMEOUT * 1000)
                                    showNotification = true;
                            }
                                
                            messageHash.get(message).put("lastSeen", currentTime);
                            messageHash.get(message).put("active", new Long(1));
                            messageHash.get(message).put("level", new Long(Math.max(result.level, messageHash.get(message).get("level"))));

                            if (showNotification)
                                notificationMessages.add(message);
                        }
                        // TODO: purge old entries
                    }
                    intent.putExtra("messageHash", messageHash);
                    sendBroadcast(intent);
                }
                if (notificationMessages.size() > 0)
                {
                    // show notification
                    String text = TextUtils.join(" +++ ", notificationMessages);
                    Notification note = new Notification(R.drawable.notification_icon, text, System.currentTimeMillis());
                    String detail = String.format("discovered %d message%s", notificationMessages.size(), notificationMessages.size() == 1 ? "" : "s");
                    Intent intent2 = new Intent(service, AhoyActivity.class);
                    intent2.setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
                    note.setLatestEventInfo(service, text, detail, PendingIntent.getActivity(service.getBaseContext(), 0, intent2, PendingIntent.FLAG_CANCEL_CURRENT));
                    note.flags = Notification.FLAG_AUTO_CANCEL;
                    notificationManager.notify(0, note);
                }
            }
            
            // if we should send a message and the AP isn't on, activate it
            if (desiredBroadcastMessage != null && !wifiManagerEx.isWifiApEnabled())
            {
                wifiManagerEx.setWifiEnabled(false);
                WifiConfiguration config = new WifiConfiguration();
                config.allowedAuthAlgorithms.clear();
                config.allowedGroupCiphers.clear();
                config.allowedKeyManagement.clear();
                config.allowedKeyManagement.set(WifiConfiguration.KeyMgmt.WPA_PSK);
                config.allowedPairwiseCiphers.clear();
                config.allowedProtocols.clear();
                String randomKey = "";
                for (int i = 0; i < 32; i++)
                    randomKey += String.format("%02x", (int)(secureRandom.nextInt(256)));
//                 Log.d(TAG, "USING RANDOM KEY: " + randomKey);
                config.preSharedKey = randomKey;
                config.SSID = messageFilter.messageToSsid(desiredBroadcastMessage);
//                 Log.d(TAG, config.toString());
                wifiManagerEx.setWifiApConfiguration(config);
                wifiManagerEx.setWifiApEnabled(config, true);
            }
            
            showSpinner = false;
            Intent intent = new Intent("AhoyActivityUpdate");
            intent.putExtra("showSpinner", showSpinner);
            sendBroadcast(intent);
            
            WifiConfiguration config = wifiManagerEx.getWifiApConfiguration();
//             Log.d(TAG, String.format("HTC: %b, WiFi enabled: %b, AP state: %d, AP SSID: %s, desired broadcast: %s", wifiManagerEx.isHtc, wifiManagerEx.isWifiEnabled(), wifiManagerEx.getWifiApState(), config.SSID, desiredBroadcastMessage));
//             Log.d(TAG, config.toString());
            
            Intent intent2 = new Intent("AhoyActivityUpdate");
            if (wifiManagerEx.isWifiApEnabled())
                intent2.putExtra("currentlyBroadcasting", messageFilter.ssidToMessage(config.SSID));
            else
                intent2.putExtra("currentlyBroadcasting", (String)null);
            sendBroadcast(intent2);
        }
        
        public void _update()
        {
//             Log.d(TAG, "updating state...");
            
            // switch off AP if it's on
            if (wifiManagerEx.isWifiApEnabled())
                wifiManagerEx.setWifiApEnabled(null, false);
            
            // switch on WiFi if it's off
            if (!wifiManagerEx.isWifiEnabled())
                wifiManagerEx.setWifiEnabled(true);
                
            boolean result = wifiManagerEx.startScan();
//             Log.d(TAG, String.format("startScan() == %b", result));
        }
        
        public void _broadcastMessage(final String message)
        {
            if (!wakeLock.isHeld())
                wakeLock.acquire();
            desiredBroadcastMessage = message;
            showSpinner = true;
            Intent intent = new Intent("AhoyActivityUpdate");
            intent.putExtra("showSpinner", showSpinner);
            sendBroadcast(intent);
            _update();
        }
        
        public void _stopBroadcast()
        {
            if (wakeLock.isHeld())
                wakeLock.release();
            desiredBroadcastMessage = null;
            showSpinner = true;
            Intent intent = new Intent("AhoyActivityUpdate");
            intent.putExtra("showSpinner", showSpinner);
            sendBroadcast(intent);
            _update();
        }
        
        public void _broadcastState()
        {
            Intent intent = new Intent("AhoyActivityUpdate");
            
            intent.putExtra("messageHash", messageHash);
            
            if (wifiManagerEx.isWifiApEnabled())
            {
                WifiConfiguration config = wifiManagerEx.getWifiApConfiguration();
                intent.putExtra("currentlyBroadcasting", messageFilter.ssidToMessage(config.SSID));
            }
            else
                intent.putExtra("currentlyBroadcasting", (String)null);
                
            intent.putExtra("showSpinner", showSpinner);
            
            sendBroadcast(intent);
        }
        
        public void run()
        {
            // save WiFi state, so we can restore it on exit
            originalWifiApEnabled = wifiManagerEx.isWifiApEnabled();
            originalWifiConfiguration = wifiManagerEx.getWifiApConfiguration();
            originalWifiEnabled = wifiManagerEx.isWifiEnabled();
            
            wifiLock = wifiManagerEx.wifiManager().createWifiLock(WifiManager.WIFI_MODE_FULL, "AhoyService");
            wifiLock.acquire();
            
//             Log.d(TAG, "Registering scanReceiver");
            registerReceiver(scanReceiver, new IntentFilter(WifiManager.SCAN_RESULTS_AVAILABLE_ACTION));
            
            _update();
            while (true)
            {
                
                long timeoutDuration = (long)((secureRandom.nextDouble() * 10.0 + 25.0) * 1000.0);
                // if we're currently broadcasting a message, wait longer
                if (desiredBroadcastMessage != null)
                    timeoutDuration *= 2;
                    
//                 Log.d(TAG, String.format("Now waiting for at most %1.2f seconds...", (float)timeoutDuration / 1000.0));
                boolean shutdown = false;
                
                do {
                    ServiceCommandWithOption commandWithOption = null;
                    try {
                        commandWithOption = commandQueue.poll(timeoutDuration, TimeUnit.MILLISECONDS);
                    } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
                    if (commandWithOption != null)
                    {
                        ServiceCommand command = commandWithOption.command;
                        if (command == ServiceCommand.SHUTDOWN)
                        {
                            shutdown = true;
                            break;
                        }
                        else if (command == ServiceCommand.NEW_BROADCAST)
                        {
                            final String message = (String)commandWithOption.option;
                            _broadcastMessage(message);
                        }
                        else if (command == ServiceCommand.STOP_BROADCAST)
                            _stopBroadcast();
                        else if (command == ServiceCommand.QUERY_STATE)
                            _broadcastState();
                        else if (command == ServiceCommand.GOT_SCAN_RESULTS)
                            _receivedScanResults();
                        else if (command == ServiceCommand.PERFORM_SCAN)
                            _update();
                    }
                    else
                    {
                        // this was a timeout, re-scan for messages
                        _update();
                    }
                } while (commandQueue.size() > 0);
                if (shutdown)
                    break;
            }
//             Log.d(TAG, "Unregistering scanReceiver");
            unregisterReceiver(scanReceiver);
            wifiLock.release();
            
            // restore WiFi configuration
//             Log.d(TAG, "Restoring WiFi configuration...");
//             Log.d(TAG, String.format("WiFi: %b, WiFiAP: %b, AP config: %s", originalWifiEnabled, originalWifiApEnabled, originalWifiConfiguration.toString()));
            wifiManagerEx.setWifiEnabled(originalWifiEnabled);
            wifiManagerEx.setWifiApConfiguration(originalWifiConfiguration);
            // Better don't re-start the AP if it was enabled. Just restore the configuration.
//             wifiManagerEx.setWifiApEnabled(originalWifiConfiguration, originalWifiApEnabled);
            
            // release wake lock if still held
            if (wakeLock.isHeld())
                wakeLock.release();

            stopSelf();
        }
    };

    @Override
    public void onCreate() {
//         Log.d(TAG, "service created");
        super.onCreate();
        serviceThread = null;
    }
    
    @Override
    public void onStart(Intent intent, int startId)
    {
//         Log.d(TAG, "service started");
        super.onStart(intent, startId);
        if (serviceThread == null)
            serviceThread = performOnBackgroundThread(new ServiceThread(this));
        queryState();
    }
    
    @Override
    public void onDestroy() {
//         Log.d(TAG, "service destroyed");
        if (serviceThread != null)
        {
            try {
                commandQueue.put(new ServiceCommandWithOption(ServiceCommand.SHUTDOWN));
            } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
            // wait until service thread has finished
            try {
                serviceThread.join();
            } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
            Log.d(TAG, "service thread has finished, shutting down service...");
            serviceThread = null;
        }
        super.onDestroy();
    }
    
    public void broadcastMessage(final String message)
    {
//         Log.d(TAG, "Broadcasting message: " + message);
        try {
            commandQueue.put(new ServiceCommandWithOption(ServiceCommand.NEW_BROADCAST, message));
        } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
    }

    public void stopBroadcast()
    {
//         Log.d(TAG, "Stopping broadcast");
        try {
            commandQueue.put(new ServiceCommandWithOption(ServiceCommand.STOP_BROADCAST));
        } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
    }
    
    public void queryState()
    {
//         Log.d(TAG, "Querying state");
        try {
            commandQueue.put(new ServiceCommandWithOption(ServiceCommand.QUERY_STATE));
        } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
    }
    
    public void gotScanResults()
    {
//         Log.d(TAG, "Got scan results");
        try {
            commandQueue.put(new ServiceCommandWithOption(ServiceCommand.GOT_SCAN_RESULTS));
        } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
    }
    
    public void performScan()
    {
//         Log.d(TAG, "Performing scan");
        try {
            commandQueue.put(new ServiceCommandWithOption(ServiceCommand.PERFORM_SCAN));
        } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
    }
    
    public String formatTime(long time)
    {
        DateFormat formatter = new SimpleDateFormat();
        Calendar calendar = Calendar.getInstance();
        calendar.setTimeInMillis(time);
        return formatter.format(calendar.getTime());
    }
}
