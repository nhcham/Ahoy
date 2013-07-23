package org.nhcham.ahoy;

import android.content.*;
import android.net.wifi.*;
import android.util.Log;
import java.lang.reflect.*;
import java.util.*;


public class WifiManagerExtended 
{
    /*
     * This class provides a WiFi interface plus AP functionality.
     * Note: enabling/disabled WiFi or AP is blocking which means the functions
     * will wait TIMEOUT seconds until the desired state is in effect.
     * Because we are doing these things in a background thread, it's the
     * most convenient way for the application.
     */
    final static String TAG = "WifiManagerExtended";
    
    final static int TIMEOUT = 30;
    
    private WifiManager wifiManager;
    private static final Map<String, Method> methodMap = new HashMap<String, Method>();
    boolean isHtc = false;
    
    public WifiManagerExtended(Context context)
    {
        wifiManager = (WifiManager) context.getSystemService(Context.WIFI_SERVICE);
        
        // check whether this is a HTC device
        try {
            Field field = WifiConfiguration.class.getDeclaredField("mWifiApProfile");
            isHtc = field != null;
        } catch (Exception e) {
        }
        
        try {
            Method method = WifiManager.class.getMethod("getWifiApState");
            methodMap.put("getWifiApState", method);
        } catch (SecurityException e) {
        } catch (NoSuchMethodException e) {
        }
        
        try {
            Method method = WifiManager.class.getMethod("getWifiApConfiguration");
            methodMap.put("getWifiApConfiguration", method);
        } catch (SecurityException e) {
        } catch (NoSuchMethodException e) {
        }
        
        try {
            Method method = WifiManager.class.getMethod(getSetWifiApConfigName(), WifiConfiguration.class);
            methodMap.put("setWifiApConfiguration", method);
        } catch (SecurityException e) {
        } catch (NoSuchMethodException e) {
        }
        
        try {
            Method method = WifiManager.class.getMethod("setWifiApEnabled", WifiConfiguration.class, boolean.class);
            methodMap.put("setWifiApEnabled", method);
        } catch (SecurityException e) {
        } catch (NoSuchMethodException e) {
        }
    }
    
    public boolean isWifiEnabled()
    {
        return wifiManager.isWifiEnabled();
    }

    public boolean isApEnabled()
    {
//         return wifiManager.isWifiEnabled();
        return false;
    }

    public boolean setWifiEnabled(boolean enabled)
    {
//         Log.d(TAG, String.format("setWifiEnabled(%b)", enabled));
        wifiManager.setWifiEnabled(enabled);
        for (int i = 0; i < TIMEOUT; i++)
        {
            if (isWifiEnabled() == enabled)
                break;
//             Log.d(TAG, "spinning...");
            try { Thread.sleep(1000); } catch (InterruptedException e) { }
        }
//         Log.d(TAG, String.format("setWifiEnabled: %b", isWifiEnabled() == enabled));
        return isWifiEnabled() == enabled;
    }

    public boolean startScan()
    {
        return wifiManager.startScan();
    }

    public List<ScanResult> getScanResults()
    {
        return wifiManager.getScanResults();
    }
    
    public int getWifiApState() {
        try {
            Method method = methodMap.get("getWifiApState");
            return (Integer)method.invoke(wifiManager);
        } catch (IllegalAccessException e) {
        } catch (InvocationTargetException e) {
        }
        return -1;
    }
    
    private WifiConfiguration getHtcWifiApConfiguration(WifiConfiguration standard)
    {
        WifiConfiguration htcWifiConfig = standard;
        try {
            Object mWifiApProfileValue = getFieldValue(standard, "mWifiApProfile");
            if (mWifiApProfileValue != null)
                htcWifiConfig.SSID = (String)getFieldValue(mWifiApProfileValue, "SSID");
        } catch (Exception e) { }
        return htcWifiConfig;
    }

    public WifiConfiguration getWifiApConfiguration() {
        WifiConfiguration configuration = null;
        try {
            Method method = methodMap.get("getWifiApConfiguration");
            configuration = (WifiConfiguration) method.invoke(wifiManager);
            if (isHtc) 
                configuration = getHtcWifiApConfiguration(configuration);
        } catch (Exception e) { }
        return configuration;
    }
    
    private void setupHtcWifiConfiguration(WifiConfiguration config) {
        try {
            Object mWifiApProfileValue = getFieldValue(config, "mWifiApProfile");

            if (mWifiApProfileValue != null) 
            {
                setFieldValue(mWifiApProfileValue, "SSID", config.SSID);
                setFieldValue(mWifiApProfileValue, "BSSID", config.BSSID);
            }
        } catch (Exception e) { }
    }
    
    public boolean setWifiApConfiguration(WifiConfiguration config) 
    {
        boolean result = false;
        try {
            if (isHtc)
                setupHtcWifiConfiguration(config);

            Method method = methodMap.get("setWifiApConfiguration");

            if (isHtc) {
                int value = (Integer) method.invoke(wifiManager, config);
                result = value > 0;
            } else {
                result = (Boolean) method.invoke(wifiManager, config);
            }
        } catch (Exception e) {
            Log.e(TAG, "", e);
        }
        return result;
    }
    
    public boolean isWifiApEnabled()
    {
        return getWifiApState() % 10 == 3;
    }
    
    public boolean setWifiApEnabled(WifiConfiguration configuration, boolean enabled)
    {
//         Log.d(TAG, String.format("setWifiApEnabled(%b)", enabled));
        boolean result = false;
        int targetWifiApState = enabled ? 3 : 1;
        try {
            Method method = methodMap.get("setWifiApEnabled");
            result = (Boolean)method.invoke(wifiManager, configuration, enabled);
        } catch (Exception e) {
            Log.e(TAG, e.getMessage(), e);
        }
        if (!result)
            return false;
            
        for (int i = 0; i < TIMEOUT; i++)
        {
            if (getWifiApState() % 10 == targetWifiApState)
                break;
//             Log.d(TAG, "spinning...");
            try { Thread.sleep(1000); } catch (InterruptedException e) { }
        }
//         Log.d(TAG, String.format("setWifiApEnabled: %b", getWifiApState() % 10 == targetWifiApState));
        return getWifiApState() % 10 == targetWifiApState;
    }

    private String getSetWifiApConfigName() 
    {
        return isHtc? "setWifiApConfig": "setWifiApConfiguration";
    }
    
    public WifiManager wifiManager()
    {
        return wifiManager;
    }
    
    private Object getFieldValue(Object object, String propertyName)  
        throws IllegalAccessException, NoSuchFieldException 
    {  
        Field field = object.getClass().getDeclaredField(propertyName);  
        field.setAccessible(true);  
        return field.get(object);  
    };  
    
    private void setFieldValue(Object object, String propertyName, Object value)  
        throws IllegalAccessException, NoSuchFieldException 
    {  
        Field field = object.getClass().getDeclaredField(propertyName);  
        field.setAccessible(true);  
        field.set(object, value);  
    };  
};
