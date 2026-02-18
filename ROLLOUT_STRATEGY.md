# Stoat-Only Gradual Rollout Strategy

## Overview

This document outlines the gradual rollout strategy for **Logiq** exclusively for **Stoat.chat**.

⚠️ **This bot is Stoat-only. There is NO Discord support or multi-platform code.**

## Rollout Phases

### Phase 1: Internal Testing (Week 1-2)
**Features**: Core features only
- Verification ✅ STABLE
- Moderation ✅ STABLE
- Status: Testing with core team

```yaml
rollout:
  features:
    verification: "stable"
    moderation: "stable"
    economy: "internal"
    leveling: "internal"
```

### Phase 2: Beta (Week 3-4)
**Features**: Economy + selected servers
- Add: Economy (50% rollout)
- Add: Leveling (50% rollout)
- Add: Tickets (25% beta whitelist)

```yaml
rollout:
  features:
    economy: "gradual"        # 50% of servers
    leveling: "gradual"
    tickets: "beta"           # Whitelist only
```

Usage:
```bash
python scripts/gradual_rollout.py --set economy 50
python scripts/gradual_rollout.py --whitelist tickets server_id_123
```

### Phase 3: Expansion (Week 5-8)
**Features**: Giveaways + increase percentages

```bash
# Increase economy rollout
python scripts/gradual_rollout.py --set economy 75

# Add giveaways to beta
python scripts/gradual_rollout.py --whitelist giveaways server_id_456

# Increase leveling
python scripts/gradual_rollout.py --set leveling 75
```

### Phase 4: Full Release (Week 9+)
**Features**: Everything enabled for all servers

```bash
python scripts/gradual_rollout.py --phase economy stable
python scripts/gradual_rollout.py --phase leveling stable
python scripts/gradual_rollout.py --phase tickets stable
python scripts/gradual_rollout.py --phase giveaways stable
```

## Rollout Commands

### Check status
```bash
python scripts/gradual_rollout.py --status
```

Output:
```
Feature Status:
  verification: stable (100%)
  moderation: stable (100%)
  economy: gradual (50%)
  leveling: gradual (50%)
  tickets: beta (25% whitelisted)
  giveaways: beta (25% whitelisted)
  social_alerts: internal (5%)
  ai_chat: internal (10%)
```

### Set rollout percentage
```bash
python scripts/gradual_rollout.py --set economy 75
python scripts/gradual_rollout.py --set leveling 75
```

### Add server to whitelist (Beta)
```bash
python scripts/gradual_rollout.py --whitelist tickets server_id_123
python scripts/gradual_rollout.py --whitelist giveaways server_id_456
```

### Remove from whitelist
```bash
python scripts/gradual_rollout.py --remove-whitelist tickets server_id_123
```

### Block server from feature
```bash
python scripts/gradual_rollout.py --blacklist economy server_id_999
```

### Advance feature to next phase
```bash
python scripts/gradual_rollout.py --phase economy stable
python scripts/gradual_rollout.py --phase tickets gradual
```

## Monitoring

### Check feature usage
```bash
python scripts/gradual_rollout.py --monitor economy

# Shows:
# - Servers with economy enabled
# - Error rates in economy feature
# - Usage statistics
```

### Export rollout config
```bash
python scripts/gradual_rollout.py --export > rollout_config.json
```

### Import rollout config
```bash
python scripts/gradual_rollout.py --import rollout_config.json
```

## Success Metrics

Track during each phase:
- **Error Rate**: Target <0.1%
- **Server Adoption**: Target >50% of eligible
- **User Satisfaction**: Track feedback
- **Performance**: API response time <500ms

## Rollback

If issues occur:
```bash
# Immediately disable feature
python scripts/gradual_rollout.py --phase economy internal

# Check what went wrong
python scripts/gradual_rollout.py --monitor economy

# Fix and re-enable
python scripts/gradual_rollout.py --set economy 25  # Lower percentage
```

## Timeline

```
Week 1-2:   Phase 1 - Internal testing (Core features)
Week 3-4:   Phase 2 - Beta (Economy, Leveling, Tickets beta)
Week 5-8:   Phase 3 - Expansion (Increase percentages)
Week 9+:    Phase 4 - Full release (Everything stable)
```

## Note

**Stoat-Only Implementation**

This bot uses:
- ✅ Pure Stoat.chat API
- ✅ Stoat WebSocket (no discord.py)
- ✅ Stoat MongoDB schema
- ❌ NO Discord support
- ❌ NO multi-platform code
- ❌ NO dual adapters

All rollout is for Stoat servers only.