# 🛡️ DB_GUARDRAILS — Garanties de cohérence Base de Données (VEO V1)

Ce document décrit les **protections mises en place au niveau de PostgreSQL** pour garantir l’intégrité des données du module VEO, indépendamment de l’API.

L’objectif est d’assurer que la base de données reste **cohérente, fiable et non contournable**, même en cas :

* d’accès SQL direct
* d’erreur applicative
* d’évolution future du backend

---

## 🎯 Philosophie

Le module VEO V1 repose sur un principe fondamental :

> **La base de données ne stocke que des données brutes (raw).
> Les métriques dérivées sont calculées à la demande côté backend.**

Les garde-fous (guardrails) DB garantissent ce principe **au niveau PostgreSQL**, en complément des validations API.

---

## 🗄️ Tables concernées

Les garde-fous s’appliquent aux tables de valeurs :

* `team_match_metric_values`
* `player_match_metric_values`

Les règles s’appuient sur les métadonnées présentes dans :

* `metric_definitions`

---

## 🔒 Guardrail 1 — Interdiction de stocker des métriques dérivées

### Problème adressé

Une métrique dérivée (`is_derived = true`) :

* ne doit **jamais** être stockée en base
* doit être **calculée dynamiquement** (analytics)

Sans protection DB, un `INSERT` SQL direct pourrait contourner l’API.

---

### Solution implémentée

Un **trigger PostgreSQL** empêche toute insertion ou mise à jour de métriques dérivées.

#### Fonction PostgreSQL

```sql
prevent_derived_metric_values()
```

#### Comportement

* Avant `INSERT` ou `UPDATE`
* Vérifie `metric_definitions.is_derived`
* Si `TRUE` → `RAISE EXCEPTION`

#### Triggers actifs

* `trg_prevent_derived_team_values`
* `trg_prevent_derived_player_values`

---

### Résultat

✔️ Impossible de stocker une métrique dérivée
✔️ Protection DB indépendante de l’API
✔️ Règle “raw-only” garantie

---

## 🔢 Guardrail 2 — Validation des métriques de type PERCENT (0–100)

### Problème adressé

Les métriques de type `PERCENT` doivent être comprises entre **0 et 100**.

La validation API est nécessaire mais **insuffisante** si quelqu’un écrit directement en base.

---

### Solution implémentée

Un **trigger PostgreSQL** valide dynamiquement la plage autorisée pour les métriques de type `PERCENT`.

#### Fonction PostgreSQL

```sql
enforce_percent_range()
```

#### Logique

* Récupère `metric_definitions.datatype`
* Si `datatype = 'PERCENT'`
* Vérifie `value_number BETWEEN 0 AND 100`
* Sinon → `RAISE EXCEPTION`

#### Triggers actifs

* `trg_enforce_percent_team_values`
* `trg_enforce_percent_player_values`

---

### Résultat

✔️ Valeurs % toujours cohérentes
✔️ Impossible d’insérer `-10` ou `150`
✔️ Validation DB + API (double sécurité)

---

## ⚡ Guardrail 3 — Indexation métier & performance

Bien que non bloquants, des **indexes orientés analytics** font partie des garanties fonctionnelles.

### Index standards (V1)

* `matches(team_id, season_id, date)`
* `players(team_id)`
* `match_player_participations(match_id)`
* `match_player_participations(player_id)`
* `team_match_metric_values(metric_id, match_id, side)`
* `player_match_metric_values(metric_id, match_id)`
* `player_match_metric_values(player_id, match_id)`

---

### Index partiel PostgreSQL (OWN)

Optimisation ciblée pour les dashboards :

```sql
CREATE INDEX ix_tmmv_own_metric_match
ON team_match_metric_values(metric_id, match_id)
WHERE side = 'OWN';
```

✔️ Accélère les lectures analytics
✔️ Transparent pour l’API
✔️ Prépare la montée en charge (V2)

---

## 🧪 Vérifications & audit

### Vérifier les triggers actifs

```sql
SELECT tgname, tgrelid::regclass
FROM pg_trigger
WHERE tgname LIKE 'trg_%';
```

### Vérifier les fonctions

```sql
SELECT proname
FROM pg_proc
WHERE proname IN (
  'prevent_derived_metric_values',
  'enforce_percent_range'
);
```

---

## ✅ État des guardrails (VEO V1)

| Règle             | Niveau | Statut |
| ----------------- | ------ | ------ |
| Raw-only metrics  | DB     | ✅      |
| Derived interdits | DB     | ✅      |
| Percent 0–100     | DB     | ✅      |
| Validation métier | API    | ✅      |
| Index analytics   | DB     | ✅      |

---

## 🧠 Conclusion

Les guardrails DB du module VEO garantissent que :

* la base reste **cohérente et fiable**
* les règles métier clés sont **inviolables**
* l’API n’est pas le seul point de vérité
* le système est **prêt pour l’usage réel** (saisie manuelle, dashboards, exports)
