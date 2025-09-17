Of course. After re-evaluating the content from the Tesla Fleet API documentation, here are the verified specifications for the energy endpoints, presented in markdown format. All information, including the examples, is a literal match to the documentation.

***

## Energy Endpoints

### backup

`POST /api/1/energy_sites/{energy_site_id}/backup`

Adjust the site's backup reserve. Visit <https://www.tesla.com/support/energy/powerwall/mobile-app/powerwall-modes#backup-reserve-anchor> for more info.

**Sample Request**

```shell
curl -X POST \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
  "backup_reserve_percent": 75
}' "https://fleet-api.prd.na.vn.cloud.tesla.com/api/1/energy_sites/<energy_site_id>/backup"
```

**Sample Response**

```json
{
  "response": {
    "reason": "",
    "result": true
  }
}
```

### backup_history

`GET /api/1/energy_sites/{energy_site_id}/calendar_history?kind=backup&start_date={start_date}&end_date={end_date}&period={period}&time_zone={time_zone}`

Returns the backup (off-grid) event history of the site in duration of seconds.

**Sample Request**

```shell
curl -X GET \
  -H "Authorization: Bearer <TOKEN>" \
  "https://fleet-api.prd.na.vn.cloud.tesla.com/api/1/energy_sites/<energy_site_id>/calendar_history?kind=backup&start_date=2023-09-01T00:00:00.000Z&end_date=2023-09-30T00:00:00.000Z&period=day&time_zone=America/Los_Angeles"
```

*(Sample Response Not Available In Docs)*

### charge_history

`GET /api/1/energy_sites/{energy_site_id}/telemetry_history?kind=charge&start_date={start_date}&end_date={end_date}&time_zone={time_zone}`

Returns the charging history of a wall connector. Energy values are in watt hours.

*(Sample Request and Response Not Available In Docs)*

### energy_history

`GET /api/1/energy_sites/{energy_site_id}/calendar_history?kind=energy&start_date={start_date}&end_date={end_date}&period={period}&time_zone={time_zone}`

Returns the energy measurements of the site, aggregated to the requested period. Energy values are in watt hours. Visit <https://www.tesla.com/support/energy/powerwall/mobile-app/energy-data> for more info.

**Sample Request**

```shell
curl -X GET \
  -H "Authorization: Bearer <TOKEN>" \
  "https://fleet-api.prd.na.vn.cloud.tesla.com/api/1/energy_sites/<energy_site_id>/calendar_history?kind=energy&start_date=2023-09-01T00:00:00.000Z&end_date=2023-09-30T00:00:00.000Z&period=day&time_zone=America/Los_Angeles"
```

**Sample Response**

```json
{
  "response": {
    "time_zone": "America/Los_Angeles",
    "entries": [
      {
        "timestamp": "2023-09-25T07:00:00Z",
        "solar_energy_exported": 6081.011666666666,
        "grid_energy_imported": 11139.99,
        "grid_services_energy_exported": 0,
        "grid_services_energy_imported": 0,
        "grid_energy_exported": 0,
        "generator_energy_exported": 0,
        "battery_energy_exported": 12108.99,
        "battery_energy_imported": 11119.588333333332,
        "consumer_energy_imported_from_solar": 8299.11,
        "consumer_energy_imported_from_battery": 12108.99,
        "consumer_energy_imported_from_grid": 11139.99,
        "consumer_energy_imported_from_generator": 0
      }
    ]
  }
}
```

### grid_import_export

`POST /api/1/energy_sites/{energy_site_id}/grid_import_export`

Allow/disallow charging from the grid and exporting energy to the grid. Visit <https://www.tesla.com/support/energy/powerwall/mobile-app/powerwall-modes#energy-exports-anchor> for more info.

**Sample Request**

```shell
curl -X POST \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
  "customer_preferred_export_rule": "pv_only"
}' "https://fleet-api.prd.na.vn.cloud.tesla.com/api/1/energy_sites/<energy_site_id>/grid_import_export"
```

**Sample Response**

```json
{
  "response": {
    "reason": "",
    "result": true
  }
}
```

### live_status

`GET /api/1/energy_sites/{energy_site_id}/live_status`

Returns the live status of the site (power, state of energy, grid status, storm mode). Power values are in watts. Energy values are in watt hours.

**Sample Request**

```shell
curl -X GET \
  -H "Authorization: Bearer <TOKEN>" \
  "https://fleet-api.prd.na.vn.cloud.tesla.com/api/1/energy_sites/<energy_site_id>/live_status"
```

**Sample Response**

```json
{
  "response": {
    "solar_power": 120,
    "energy_left": 27010.88,
    "total_pack_energy": 27000,
    "percentage_charged": 100,
    "battery_power": -2560,
    "load_power": 2680,
    "grid_status": "Active",
    "grid_power": 0,
    "grid_services_power": 0,
    "generator_power": 0,
    "storm_mode_active": false,
    "timestamp": "2023-11-20T17:15:35-08:00"
  }
}
```

### off_grid_vehicle_charging_reserve

`POST /api/1/energy_sites/{energy_site_id}/off_grid_vehicle_charging_reserve`

Adjust the site's off-grid vehicle charging backup reserve. Visit <https://www.tesla.com/support/energy/powerwall/mobile-app/vehicle-charging-during-power-outage> for more info.

**Sample Request**

```shell
curl -X POST \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
  "off_grid_vehicle_charging_reserve_percent": 50
}' "https://fleet-api.prd.na.vn.cloud.tesla.com/api/1/energy_sites/<energy_site_id>/off_grid_vehicle_charging_reserve"
```

**Sample Response**

```json
{
  "response": {
    "reason": "",
    "result": true
  }
}
```

### operation

`POST /api/1/energy_sites/{energy_site_id}/operation`

Set the site's mode. Use `autonomous` for time-based control and `self_consumption` for self-powered mode. Visit <https://www.tesla.com/support/energy/powerwall/mobile-app/powerwall-modes> for more info.

**Sample Request**

```shell
curl -X POST \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
  "default_real_mode": "self_consumption"
}' "https://fleet-api.prd.na.vn.cloud.tesla.com/api/1/energy_sites/<energy_site_id>/operation"
```

**Sample Response**

```json
{
  "response": {
    "reason": "",
    "result": true
  }
}
```

### products

`GET /api/1/products`

Returns products mapped to user.

**Sample Request**

```shell
curl -X GET \
  -H "Authorization: Bearer <TOKEN>" \
  "https://fleet-api.prd.na.vn.cloud.tesla.com/api/1/products"
```

**Sample Response**

```json
{
  "response": [
    {
      "energy_site_id": 1234567890,
      "asset_site_id": "S:1234567890",
      "components": {
        "battery": true,
        "battery_type": "solar_powerwall",
        "solar": true,
        "solar_type": "pv_inverter",
        "grid": true,
        "load_meter": true
      },
      "vehicle_count": 1,
      "installation_date": "2020-08-28T19:24:22-07:00"
    }
  ],
  "count": 1
}
```

### site_info

`GET /api/1/energy_sites/{energy_site_id}/site_info`

Returns information about the site. Things like assets (has solar, etc), settings (backup reserve, etc), and features (storm_mode_capable, etc). Power values are in watts. Energy values are in watt hours. `default_real_mode` can be `autonomous` for time-based control and `self_consumption` for self-powered mode.

**Sample Request**

```shell
curl -X GET \
  -H "Authorization: Bearer <TOKEN>" \
  "https://fleet-api.prd.na.vn.cloud.tesla.com/api/1/energy_sites/<energy_site_id>/site_info"
```

**Sample Response**

```json
{
  "response": {
    "id": "1234567890",
    "site_name": "My House",
    "asset_site_id": "S:1234567890",
    "components": {
      "solar": true,
      "solar_type": "pv_inverter",
      "battery": true,
      "grid": true,
      "load_meter": true,
      "market_type": "residential"
    },
    "backup_reserve_percent": 20,
    "default_real_mode": "self_consumption",
    "version": "23.28 92095182",
    "battery_count": 2
  }
}
```

### storm_mode

`POST /api/1/energy_sites/{energy_site_id}/storm_mode`

Update storm watch participation. Visit <https://www.tesla.com/support/energy/powerwall/mobile-app/storm-watch> for more info.

**Sample Request**

```shell
curl -X POST \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
  "enabled": true
}' "https://fleet-api.prd.na.vn.cloud.tesla.com/api/1/energy_sites/<energy_site_id>/storm_mode"
```

**Sample Response**

```json
{
  "response": {
    "reason": "",
    "result": true
  }
}
```

### time_of_use_settings

`POST /api/1/energy_sites/{energy_site_id}/time_of_use_settings`

Update the time of use settings for the energy site. Visit <https://www.tesla.com/support/energy/powerwall/mobile-app/utility-rate-plans> for more information about Utility Rate Plans. The payload for this request that should be passed in for `tou_settings.tariff_content_v2` is a tariff structure.

Update the time of use settings for the energy site. Visit <https://www.tesla.com/support/energy/powerwall/mobile-app/utility-rate-plans> for more information about Utility Rate Plans. The payload for this request that should be passed in for tou_settings.tariff_content_v2 is a tariff structure. Visit <https://digitalassets-energy.tesla.com/raw/upload/app/fleet-api/example-tariff/PGE-EV2-A.json> for an example. Please note the following when creating the payload:

At least one season must be present. Seasons can have arbitrary names as they are just a way to distinguish rates for specific times of the year. Each season contains a tariff period specifying the start and end months/days along with its time of use periods.
demand_charges is for tariffs that charge a fee for peak power consumption. This is not common for residential systems. Typically residential customers are only charged for the energy that they consume, energy_charges should be used in this case.
Prices in ALL in energy_charges or demand_charges apply to all time periods. It is recommended to use the ALL field for flat/fixed tariffs instead of creating tariff periods.
The following are valid currency strings: USD, EUR, GBP
Time of use labels may be any string but the mobile app will only support displaying the following labels: ON_PEAK, OFF_PEAK, PARTIAL_PEAK or SUPER_OFF_PEAK.
The tariff must pass the following validation checks:
No overlaps of time periods
No gaps in time periods
No overlapping seasons or gaps between seasons
All periods/seasons that have prices defined have time periods defined
All periods/seasons that have time periods defined have prices
No negative prices. Negative prices will be rounded to zero. Therefore use prices that include taxes. This will limit the frequency of negative prices occurring.
Buy price should be >= sell price at any given time. If not, the buy price will be set equal to the sell price.

**Sample Request**

```shell
curl -X POST \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
  "tou_settings": {
    "tariff_content_v2": {
  "version": 1,
  "monthly_minimum_bill": 0,
  "min_applicable_demand": 0,
  "max_applicable_demand": 0,
  "monthly_charges": 0,
  "utility": "Pacific Gas & Electric Co",
  "code": "PGE-EV-2A-TOU",
  "name": "Residential - Time of Use - Plug-In Electric Vehicle 2 (NEM 2.0)",
  "currency": "USD",
  "daily_charges": [{ "name": "Charge", "amount": 0 }],
  "daily_demand_charges": {},
  "demand_charges": { "ALL": { "rates": { "ALL": 0 } }, "Summer": { "rates": {} }, "Winter": { "rates": {} } },
  "energy_charges": {
    "ALL": { "rates": { "ALL": 0 } },
    "Summer": {
      "rates": { "PARTIAL_PEAK": 0.4138, "ON_PEAK": 0.4305, "OFF_PEAK": 0.2451 }
    },
    "Winter": {
      "rates": { "PARTIAL_PEAK": 0.4471, "ON_PEAK": 0.5576, "OFF_PEAK": 0.2451 }
    }
  },
  "seasons": {
    "Summer": {
      "toDay": 31,
      "fromDay": 1,
      "tou_periods": {
        "PARTIAL_PEAK": {
          "periods": [
            { "fromDayOfWeek": 0, "toHour": 16, "toDayOfWeek": 6, "fromHour": 15, "fromMinute": 0, "toMinute": 0 },
            { "fromDayOfWeek": 0, "toHour": 0, "toDayOfWeek": 6, "fromHour": 21, "fromMinute": 0, "toMinute": 0 }
          ]
        },
        "ON_PEAK": {
          "periods": [
            { "fromDayOfWeek": 0, "toHour": 21, "toDayOfWeek": 6, "fromHour": 16, "fromMinute": 0, "toMinute": 0 }
          ]
        },
        "OFF_PEAK": {
          "periods": [
            { "fromDayOfWeek": 0, "toHour": 15, "toDayOfWeek": 6, "fromHour": 0, "fromMinute": 0, "toMinute": 0 }
          ]
        }
      },
      "toMonth": 5,
      "fromMonth": 10
    },
    "Winter": {
      "toDay": 30,
      "fromDay": 1,
      "tou_periods": {
        "PARTIAL_PEAK": {
          "periods": [
            { "fromDayOfWeek": 0, "toHour": 16, "toDayOfWeek": 6, "fromHour": 15, "fromMinute": 0, "toMinute": 0 },
            { "fromDayOfWeek": 0, "toHour": 0, "toDayOfWeek": 6, "fromHour": 21, "fromMinute": 0, "toMinute": 0 }
          ]
        },
        "ON_PEAK": {
          "periods": [
            { "fromDayOfWeek": 0, "toHour": 21, "toDayOfWeek": 6, "fromHour": 16, "fromMinute": 0, "toMinute": 0 }
          ]
        },
        "OFF_PEAK": {
          "periods": [
            { "fromDayOfWeek": 0, "toHour": 15, "toDayOfWeek": 6, "fromHour": 0, "fromMinute": 0, "toMinute": 0 }
          ]
        }
      },
      "toMonth": 9,
      "fromMonth": 6
    }
  },
  "sell_tariff": {
    "min_applicable_demand": 0,
    "monthly_minimum_bill": 0,
    "monthly_charges": 0,
    "max_applicable_demand": 0,
    "utility": "Pacific Gas & Electric Co",
    "demand_charges": { "ALL": { "rates": { "ALL": 0 } }, "Summer": { "rates": {} }, "Winter": { "rates": {} } },
    "daily_charges": [{ "name": "Charge", "amount": 0 }],
    "seasons": {
      "Summer": {
        "toDay": 31,
        "fromDay": 1,
        "tou_periods": {
          "PARTIAL_PEAK": {
            "periods": [
              {
                "fromDayOfWeek": 0,
                "toHour": 16,
                "toDayOfWeek": 6,
                "fromHour": 15,
                "fromMinute": 0,
                "toMinute": 0
              },
              { "fromDayOfWeek": 0, "toHour": 0, "toDayOfWeek": 6, "fromHour": 21, "fromMinute": 0, "toMinute": 0 }
            ]
          },
          "ON_PEAK": {
            "periods": [
              { "fromDayOfWeek": 0, "toHour": 21, "toDayOfWeek": 6, "fromHour": 16, "fromMinute": 0, "toMinute": 0 }
            ]
          },
          "OFF_PEAK": {
            "periods": [
              { "fromDayOfWeek": 0, "toHour": 15, "toDayOfWeek": 6, "fromHour": 0, "fromMinute": 0, "toMinute": 0 }
            ]
          }
        },
        "toMonth": 5,
        "fromMonth": 10
      },
      "Winter": {
        "toDay": 30,
        "fromDay": 1,
        "tou_periods": {
          "PARTIAL_PEAK": {
            "periods": [
              {
                "fromDayOfWeek": 0,
                "toHour": 16,
                "toDayOfWeek": 6,
                "fromHour": 15,
                "fromMinute": 0,
                "toMinute": 0
              },
              { "fromDayOfWeek": 0, "toHour": 0, "toDayOfWeek": 6, "fromHour": 21, "fromMinute": 0, "toMinute": 0 }
            ]
          },
          "ON_PEAK": {
            "periods": [
              { "fromDayOfWeek": 0, "toHour": 21, "toDayOfWeek": 6, "fromHour": 16, "fromMinute": 0, "toMinute": 0 }
            ]
          },
          "OFF_PEAK": {
            "periods": [
              { "fromDayOfWeek": 0, "toHour": 15, "toDayOfWeek": 6, "fromHour": 0, "fromMinute": 0, "toMinute": 0 }
            ]
          }
        },
        "toMonth": 9,
        "fromMonth": 6
      }
    },
    "code": "",
    "energy_charges": {
      "ALL": { "rates": { "ALL": 0 } },
      "Summer": {
        "rates": { "PARTIAL_PEAK": 0.4138, "ON_PEAK": 0.4305, "OFF_PEAK": 0.2451 }
      },
      "Winter": {
        "rates": { "PARTIAL_PEAK": 0.4471, "ON_PEAK": 0.5576, "OFF_PEAK": 0.2451 }
      }
    },
    "daily_demand_charges": {},
    "currency": "",
    "name": "Residential - Time of Use - Plug-In Electric Vehicle 2 (NEM 2.0)"
  }
}' "https://fleet-api.prd.na.vn.cloud.tesla.com/api/1/energy_sites/<energy_site_id>/time_of_use_settings"
```

**Sample Response**

```json
{
  "response": {
    "reason": "",
    "result": true
  }
}
```
