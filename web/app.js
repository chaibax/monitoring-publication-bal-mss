/* Rendu de la page depuis les agrégats produits par le pipeline.
   Aucun appel à un service tiers : tout vient du même déploiement.
   Principe directeur : ce qui est publié, ce sont des dénombrements. Les
   seules qualifications portent sur la chaîne nationale et ses maillons. */

const SEUIL_REGROUPEMENT = 30;   // décision 3 : voir docs/journal.md
const JOURS_CHRONO = 30;
const PEREMPTION_HEURES = 48;  // au-delà, l'outil est réputé en panne

const ETATS = {
  soleil:       { pic: "pic-soleil",       nom: "Soleil" },
  voile:        { pic: "pic-voile",        nom: "Ciel voilé" },
  nuage:        { pic: "pic-nuage",        nom: "Nuage" },
  pluie:        { pic: "pic-pluie",        nom: "Pluie" },
  brouillard:   { pic: "pic-brouillard",   nom: "Brouillard" },
  indisponible: { pic: "pic-indisponible", nom: "Non instrumenté" },
  absent:       { pic: "pic-absent",       nom: "Aucun fichier produit" },
};

const nf = new Intl.NumberFormat("fr-FR");
const df = new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "long", year: "numeric" });

const $ = (id) => document.getElementById(id);
const jourDe = (iso) => df.format(new Date(iso + "T12:00:00"));

function duree(secondes) {
  if (secondes === null || secondes === undefined) return "délai inconnu";
  const s = Math.abs(secondes);
  if (s < 60) return `${s} s`;
  const m = Math.floor(s / 60), r = s % 60;
  if (m < 60) return r ? `${m} min ${r} s` : `${m} min`;
  return `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, "0")}`;
}

async function json(chemin) {
  const r = await fetch(chemin, { cache: "no-cache" });
  if (!r.ok) throw new Error(`${chemin} : ${r.status}`);
  return r.json();
}

/* ---------- Bulletin météo ---------- */

function maillon(titre, etat, justification) {
  const e = ETATS[etat];
  return `<div class="maillon etat-${etat}">
    <p class="maillon__titre">${titre}</p>
    <div class="maillon__etat">
      <svg role="img" aria-label="${e.nom}"><use href="#${e.pic}"></use></svg>
      <span class="maillon__nom">${e.nom}</span>
    </div>
    <p class="maillon__justification">${justification}</p>
  </div>`;
}

function ageHeures(dernier) {
  return (Date.now() - new Date(dernier.source_timestamp + "+02:00")) / 3600000;
}

function etatAlimentation(dernier) {
  if (!dernier) {
    return ["brouillard", "Aucun relevé disponible. L'outil est en difficulté, ce qui ne dit rien de la chaîne."];
  }
  // Sans ce contrôle, une panne de l'outil laisserait la page afficher
  // indéfiniment le dernier état favorable qu'il a connu.
  const age = ageHeures(dernier);
  if (age > PEREMPTION_HEURES) {
    return ["brouillard", `Aucun relevé depuis <b>${Math.floor(age / 24)} jours</b>.
      L'outil ne produit plus&nbsp;: cet écran ne dit rien de l'état réel de la chaîne.`];
  }
  const heure = dernier.source_timestamp.slice(11, 16);
  if (dernier.statut === "indetermine") {
    return ["brouillard", `Fichier produit à ${heure}, mais les volumes ne sont pas
      calculables : il n'existe pas encore d'observation de la veille à laquelle comparer.`];
  }
  if (dernier.statut === "interrompu") {
    return ["pluie", `Fichier régénéré à ${heure} mais <b>identique au précédent</b> :
      aucune donnée nouvelle n'a été produite.`];
  }
  const c = dernier.national.creations;
  if (c > 0) {
    return ["soleil", `<b>${nf.format(c)}</b> adresses nouvellement publiées,
      ${nf.format(dernier.national.suppressions)} retirées. Fichier produit à ${heure}.`];
  }
  return ["nuage", `Aucune adresse nouvellement publiée. Fichier produit à ${heure} :
    la chaîne a fonctionné, elle n'a rien apporté de nouveau.`];
}

function etatDiffusion(dernier) {
  const d = dernier && dernier.diffusion;
  if (!d || !d.mesure) {
    return ["brouillard", "Le miroir data.gouv.fr n'a pas pu être interrogé lors du dernier cycle."];
  }
  const t = d.delai_secondes;
  if (t < 0) return ["nuage", `Dépôt sur data.gouv.fr antérieur à la génération par l'ANS :
    les deux sources sont incohérentes de ${duree(t)}.`];
  if (t > 6 * 3600) return ["voile", `data.gouv.fr accuse <b>${duree(t)}</b> de retard sur
    l'extraction de l'ANS. Le fichier est produit, sa rediffusion traîne.`];
  return ["soleil", `Fichier repris par data.gouv.fr <b>${duree(t)}</b> après sa
    génération par l'ANS.`];
}

function etatRestitution() {
  return ["indisponible", `Les sondes témoins ne sont pas encore en service. Aucune
    mesure n'est disponible pour ce maillon : un état favorable affiché faute de mesure
    serait un mensonge par omission.`];
}

/* ---------- Chronologie ---------- */

function derniersJours(n, finIso) {
  const fin = new Date(finIso + "T12:00:00"), jours = [];
  for (let i = n - 1; i >= 0; i--) {
    const d = new Date(fin);
    d.setDate(d.getDate() - i);
    jours.push(d.toISOString().slice(0, 10));
  }
  return jours;
}

const MOIS_COURT = new Intl.DateTimeFormat("fr-FR", { month: "short" });

function bandeChrono(titre, jours, cellule) {
  // L'étiquette est dans la même colonne que la case : au retour à la ligne
  // sur petit écran, la date reste collée au jour qu'elle désigne.
  const colonnes = jours.map((j) => {
    const { classe, etat, texte } = cellule(j);
    const pic = etat ? `<svg aria-hidden="true"><use href="#${ETATS[etat].pic}"></use></svg>` : "";
    const d = new Date(j + "T12:00:00");
    const debutDeMois = d.getDate() === 1;
    // Le mois passe à la ligne : une étiquette large déformerait la grille
    // et ferait déborder la bande sur deux rangs.
    const etiquette = debutDeMois
      ? `1<span class="chrono-mois">${MOIS_COURT.format(d).replace(".", "")}</span>`
      : d.getDate();
    return `<div class="chrono-col${debutDeMois ? " debut-de-mois" : ""}">
      <div class="chrono-jour ${classe} ${etat ? "etat-" + etat : ""}"
        title="${jourDe(j)} — ${texte}"><span class="fr-sr-only">${jourDe(j)} : ${texte}</span>${pic}</div>
      <span class="chrono-etiquette" aria-hidden="true">${etiquette}</span>
    </div>`;
  }).join("");
  const debut = jourDe(jours[0]), fin = jourDe(jours[jours.length - 1]);
  return `<div class="chrono-ligne">
    <p class="chrono-titre">${titre} <span class="chrono-periode">du ${debut} au ${fin}</span></p>
    <div class="chrono-bande">${colonnes}</div></div>`;
}

function rendreChronologie(calendrier, agregats, aujourdhui) {
  const jours = derniersJours(JOURS_CHRONO, aujourdhui);
  $("chronologie").innerHTML =
    // Un jour que l'outil a mesuré est un jour produit, même si le miroir
    // n'avait pas encore reçu le fichier quand le calendrier a été rafraîchi.
    bandeChrono("Production du fichier par la chaîne", jours, (j) =>
      (calendrier.calendrier[j] || agregats[j])
        ? { classe: "", etat: "soleil", texte: "fichier produit" }
        : { classe: "absent", etat: "absent", texte: "aucun fichier produit" }) +
    bandeChrono("Volumes publiés, mesurés par l'outil", jours, (j) => {
      const a = agregats[j];
      if (!a) return { classe: "hachure", etat: null, texte: "hors période d'observation de l'outil" };
      if (a.statut === "indetermine") return { classe: "", etat: "brouillard", texte: "volumes non calculables" };
      if (a.statut === "interrompu") return { classe: "", etat: "pluie", texte: "fichier identique au précédent" };
      return a.national.creations > 0
        ? { classe: "", etat: "soleil", texte: `${nf.format(a.national.creations)} adresses publiées` }
        : { classe: "", etat: "nuage", texte: "aucune adresse publiée" };
    });
}

/* ---------- Histogramme ---------- */

function rendreHistogramme(calendrier, agregats, aujourdhui) {
  const jours = derniersJours(90, aujourdhui);
  const mesures = jours.map((j) => (agregats[j] && agregats[j].national.creations !== null)
    ? agregats[j].national.creations : null);
  const connus = mesures.filter((v) => v !== null);

  if (!connus.length) {
    $("histogramme").innerHTML = `<div class="histo-vide">
      <p class="fr-mb-1w"><b>La série des volumes commence le ${jourDe(aujourdhui)}.</b></p>
      <p class="fr-text--sm fr-mb-0">Le fichier source ne porte aucune date de création :
      les volumes publiés avant la mise en service de l'outil ne sont pas reconstituables.
      Seule la production du fichier, elle, est connue depuis le
      ${jourDe(calendrier.premier_jour)} — voir la chronologie ci-dessus.</p></div>`;
    $("histogramme-texte").innerHTML = "<p>Aucune valeur mesurée à ce jour.</p>";
    return;
  }
  const max = Math.max(...connus);
  $("histogramme").innerHTML = `<div class="histo">` + jours.map((j, i) => {
    const v = mesures[i];
    if (v === null) return `<div class="histo-barre manquante" title="${jourDe(j)} — données manquantes"></div>`;
    if (v === 0) return `<div class="histo-barre nulle" title="${jourDe(j)} — aucune publication"></div>`;
    return `<div class="histo-barre" style="height:${Math.max(2, (v / max) * 100)}%"
      title="${jourDe(j)} — ${nf.format(v)} adresses publiées"></div>`;
  }).join("") + `</div>`;
  $("histogramme-texte").innerHTML = "<ul>" + jours.map((j, i) =>
    `<li>${jourDe(j)} : ${mesures[i] === null ? "données manquantes" : nf.format(mesures[i])}</li>`
  ).join("") + "</ul>";
}

/* ---------- Par domaine ---------- */

function rendreDomaines(instantane, dernier) {
  if (!instantane) { $("domaines").innerHTML = "<p>Aucun relevé par domaine.</p>"; return; }

  const mouvements = (dernier && dernier.domaines) || {};
  const mesure = dernier && dernier.statut !== "indetermine";
  const tous = Object.entries(instantane).map(([domaine, volume]) => {
    const m = mouvements[domaine];
    return {
      domaine,
      total: m ? m[0] : volume,
      publiees: m ? m[1] : (mesure ? 0 : null),
      retirees: m ? m[2] : (mesure ? 0 : null),
    };
  });

  const publies = tous.filter((d) => d.total >= SEUIL_REGROUPEMENT);
  const petits = tous.filter((d) => d.total < SEUIL_REGROUPEMENT);
  const cumul = (champ) => petits.reduce((s, d) => s + (d[champ] || 0), 0);

  const COLONNES = [
    { cle: "domaine",  libelle: "Domaine",          nombre: false },
    { cle: "total",    libelle: "Boîtes publiées",  nombre: true },
    { cle: "publiees", libelle: "Publiées ce jour", nombre: true },
    { cle: "retirees", libelle: "Retirées ce jour", nombre: true },
  ];

  let tri = { cle: "total", sens: "desc" };

  function trier(lignes) {
    const { cle, sens } = tri;
    const signe = sens === "asc" ? 1 : -1;
    return [...lignes].sort((a, b) => {
      if (cle === "domaine") return signe * a.domaine.localeCompare(b.domaine, "fr");
      const va = a[cle] === null ? -1 : a[cle];
      const vb = b[cle] === null ? -1 : b[cle];
      // À valeur égale, l'ordre alphabétique tranche : le classement reste
      // stable d'un affichage à l'autre plutôt que de dépendre du hasard.
      return va === vb ? a.domaine.localeCompare(b.domaine, "fr") : signe * (va - vb);
    });
  }

  function cellule(valeur) {
    return valeur === null ? "—" : nf.format(valeur);
  }

  function dessiner() {
    const lignes = trier(publies).map((d) => `<tr>
      <td>${d.domaine}</td>
      <td class="nombre">${nf.format(d.total)}</td>
      <td class="nombre">${cellule(d.publiees)}</td>
      <td class="nombre">${cellule(d.retirees)}</td></tr>`).join("");

    const entetes = COLONNES.map((c) => {
      const actif = tri.cle === c.cle;
      const sensAria = actif ? (tri.sens === "asc" ? "ascending" : "descending") : "none";
      const fleche = actif ? (tri.sens === "asc" ? "▲" : "▼") : "";
      const prochain = actif && tri.sens === "desc" ? "croissant" : "décroissant";
      return `<th scope="col" class="${c.nombre ? "nombre" : ""}" aria-sort="${sensAria}">
        <button type="button" class="tri" data-cle="${c.cle}"
          title="Trier par ${c.libelle.toLowerCase()}, ordre ${prochain}">
          ${c.libelle}<span class="tri-fleche" aria-hidden="true">${fleche}</span></button></th>`;
    }).join("");

    $("domaines").innerHTML = `
      <p class="fr-text--sm">${nf.format(publies.length)} domaines comptant au moins
      ${SEUIL_REGROUPEMENT} boîtes sont affichés individuellement. Les
      ${nf.format(petits.length)} autres, qui totalisent ${nf.format(cumul("total"))} boîtes,
      sont regroupés sur la dernière ligne. Cliquez sur un en-tête pour changer le tri.</p>
      <div class="enveloppe-defilante"><table class="tableau-domaines">
        <caption class="fr-sr-only">Volumes et mouvements par domaine de messagerie,
          triés par ${COLONNES.find((c) => c.cle === tri.cle).libelle.toLowerCase()},
          ordre ${tri.sens === "asc" ? "croissant" : "décroissant"}</caption>
        <thead><tr>${entetes}</tr></thead>
        <tbody>${lignes}
          <tr class="regroupement"><td>autres domaines (moins de ${SEUIL_REGROUPEMENT} boîtes)</td>
          <td class="nombre">${nf.format(cumul("total"))}</td>
          <td class="nombre">${mesure ? nf.format(cumul("publiees")) : "—"}</td>
          <td class="nombre">${mesure ? nf.format(cumul("retirees")) : "—"}</td></tr>
        </tbody></table></div>`;

    $("domaines").querySelectorAll("button.tri").forEach((bouton) => {
      bouton.addEventListener("click", () => {
        const cle = bouton.dataset.cle;
        if (tri.cle === cle) {
          tri.sens = tri.sens === "desc" ? "asc" : "desc";
        } else {
          // Un volume se lit d'abord du plus grand au plus petit, un nom
          // d'abord de A à Z.
          tri = { cle, sens: cle === "domaine" ? "asc" : "desc" };
        }
        dessiner();
      });
    });
  }

  dessiner();
}

/* ---------- Journal ---------- */

function rendreJournal(calendrier) {
  const trous = [...calendrier.interruptions].reverse();
  if (!trous.length) { $("journal").innerHTML = "<p>Aucune interruption observée.</p>"; return; }
  $("journal").innerHTML = `<p class="fr-text--sm">Jours sans production de fichier,
    reconstitués depuis l'historique des dépôts, du ${jourDe(calendrier.premier_jour)} au
    ${jourDe(calendrier.dernier_jour)}.</p>
    <table class="tableau-domaines">
      <caption class="fr-sr-only">Interruptions de production observées</caption>
      <thead><tr><th scope="col">Début</th><th scope="col">Fin</th>
        <th scope="col" class="nombre">Durée</th><th scope="col">Périmètre</th></tr></thead>
      <tbody>${trous.map((t) => `<tr><td>${jourDe(t.debut)}</td><td>${jourDe(t.fin)}</td>
        <td class="nombre">${t.jours} j</td><td>national — aucun fichier produit</td></tr>`).join("")}
      </tbody></table>
    <p class="fr-text--xs fr-mt-1w note-lecture"><b>Lecture&nbsp;:</b> ces interruptions
    portent sur la production du fichier. L'outil constate une absence&nbsp;; il n'en
    qualifie ni la cause ni la responsabilité.</p>`;
}

/* ---------- Tuiles ---------- */

function tuile(valeur, libelle, source) {
  return `<div class="fr-col-12 fr-col-md-3"><div class="tuile-cle">
    <p class="tuile-cle__valeur">${valeur}</p>
    <p class="tuile-cle__libelle">${libelle}</p>
    <p class="tuile-cle__source">${source}</p></div></div>`;
}

function rendreTuiles(dernier, calendrier, instantane) {
  const total = dernier ? dernier.national.total_bal : null;
  const domaines = instantane ? Object.keys(instantane).length : null;
  const heure = dernier ? dernier.source_timestamp.slice(11, 16) : "—";
  const ages = Math.floor((Date.now() - new Date(dernier.source_timestamp + "+02:00")) / 86400000);
  $("tuiles").innerHTML =
    tuile(total !== null ? nf.format(total) : "—", "boîtes publiées dans l'Annuaire Santé", "extraction ANS") +
    tuile(dernier && dernier.national.creations !== null ? nf.format(dernier.national.creations) : "—",
          "adresses nouvellement publiées ce jour", "calcul par différence d'ensembles") +
    tuile(domaines !== null ? nf.format(domaines) : "—", "domaines de messagerie observés", "extraction ANS") +
    tuile(`${heure}`, `dernière production effective · ${ages <= 0 ? "aujourd'hui" : ages + " j"}`,
          "horodatage de génération ANS");
}

/* ---------- Assemblage ---------- */

async function demarrer() {
  let index, calendrier, instantane = null;
  try {
    [index, calendrier] = await Promise.all([json("data/index.json"), json("data/calendrier-publications.json")]);
  } catch (e) {
    $("fraicheur").innerHTML = `<b>Les relevés n'ont pas pu être chargés.</b> L'outil est
      en difficulté, ce qui ne dit rien de l'état de la chaîne MSSanté.`;
    $("bulletin").innerHTML = maillon("Alimentation et publication dans l'Annuaire Santé", "brouillard", "Aucune donnée.")
      + maillon("Diffusion sur data.gouv.fr", "brouillard", "Aucune donnée.")
      + maillon("Restitution sur les fiches", ...etatRestitution());
    return;
  }

  const agregats = {};
  for (const j of index.jours) { try { agregats[j] = await json(`data/daily/${j}.json`); } catch (e) {} }
  if (index.instantane) { try { instantane = await json(`data/${index.instantane}`); } catch (e) {} }

  const aujourdhui = index.jours.length ? index.jours[index.jours.length - 1] : calendrier.dernier_jour;
  const dernier = agregats[aujourdhui] || null;

  $("badge-date").textContent = `Données au ${jourDe(aujourdhui)}`;
  if (dernier) {
    const h = ageHeures(dernier);
    const age = h < 24 ? `il y a ${Math.max(0, Math.round(h))} h`
                       : `il y a ${Math.floor(h / 24)} jours`;
    $("fraicheur").innerHTML = `Dernière production effective de la chaîne&nbsp;:
      <b>${jourDe(aujourdhui)} à ${dernier.source_timestamp.slice(11, 16)}</b>,
      heure de génération par l'ANS — <b>${age}</b>.
      ${h > PEREMPTION_HEURES
        ? `<span class="fr-badge fr-badge--error fr-badge--sm fr-ml-1w">Données périmées</span>`
        : ""}`;
  } else {
    $("fraicheur").innerHTML = `<b>Aucun relevé de l'outil.</b> L'âge des données est inconnu.`;
  }

  $("bulletin").innerHTML =
    maillon("Alimentation et publication dans l'Annuaire Santé", ...etatAlimentation(dernier)) +
    maillon("Diffusion sur data.gouv.fr", ...etatDiffusion(dernier)) +
    maillon("Restitution sur les fiches", ...etatRestitution());

  rendreChronologie(calendrier, agregats, aujourdhui);

  const publies = instantane ? Object.values(instantane).filter((n) => n >= SEUIL_REGROUPEMENT).length : 0;
  $("phrase-lecture").innerHTML = dernier
    ? `Au ${jourDe(aujourdhui)}, l'Annuaire Santé publie <b>${nf.format(dernier.national.total_bal)}</b>
       boîtes aux lettres MSSanté réparties sur <b>${nf.format(Object.keys(instantane || {}).length)}</b>
       domaines de messagerie, dont ${nf.format(publies)} comptent au moins ${SEUIL_REGROUPEMENT} boîtes.
       ${dernier.national.creations === null
         ? `Les volumes publiés ce jour ne sont pas encore calculables : l'outil vient d'être mis en service et n'a pas d'observation de la veille à laquelle comparer.`
         : `<b>${nf.format(dernier.national.creations)}</b> adresses ont été nouvellement publiées et <b>${nf.format(dernier.national.suppressions)}</b> retirées depuis la veille.`}
       Sur les ${calendrier.jours_publies} jours observés depuis le ${jourDe(calendrier.premier_jour)},
       la chaîne a produit un fichier <b>${calendrier.jours_publies} fois</b>, avec
       <b>${calendrier.interruptions.length} interruptions</b>, dont une de
       <b>${Math.max(...calendrier.interruptions.map((t) => t.jours))} jours</b>.`
    : `Aucun relevé disponible.`;

  rendreTuiles(dernier, calendrier, instantane);
  rendreHistogramme(calendrier, agregats, aujourdhui);
  rendreDomaines(instantane, dernier);
  rendreJournal(calendrier);
}

demarrer();
