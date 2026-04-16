import React, { useState, useRef } from 'react';

const MedicalMap = ({ onCoordinatesClick, onDeleteInjury, onEditInjury, injuries = [] }) => {
  const imageRef = useRef(null);
  const [hoveredInjury, setHoveredInjury] = useState(null);
  const [restrictionDate, setRestrictionDate] = useState('');
  const [restrictionType, setRestrictionType] = useState('no_sport');

  const handleImageClick = (e) => {
    if (!imageRef.current) return;

    const rect = imageRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;

    onCoordinatesClick?.({ coord_x: x, coord_y: y });
  };

  const handleDelete = (e, injuryId) => {
    e.stopPropagation();
    if (window.confirm('Voulez-vous vraiment supprimer cette blessure ?')) {
      onDeleteInjury?.(injuryId);
    }
  };

  function getTotalInjuryDays(injuries) {
    const today = new Date();
    return injuries.reduce((total, injury) => {
      const start = new Date(injury.injury_date);
      let end = injury.injury_end_date ? new Date(injury.injury_end_date) : today;
      if (end > today) end = today; // Si la date de fin est dans le futur, on prend aujourd'hui
      const diff = Math.ceil((end - start) / (1000 * 60 * 60 * 24));
      return total + (diff > 0 ? diff : 0);
    }, 0);
  }
  const totalDays = getTotalInjuryDays(injuries);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Colonne gauche : Image du corps */}
      <div className="relative">
        <h3 className="font-semibold text-gray-700 mb-3 text-center">Cliquez sur la zone blessée</h3>
        <div className="relative sticky top-4">
          <img
            ref={imageRef}
            src="/images/body-anatomy.jpg"
            alt="Anatomie du corps humain"
            className="w-full h-auto cursor-crosshair rounded-lg shadow-lg border-2 border-gray-200"
            onClick={handleImageClick}
          />
          
          {/* Overlay SVG pour afficher les marqueurs */}
          <svg
            className="absolute top-0 left-0 w-full h-full pointer-events-none"
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
          >
            {injuries.map((injury) => {
              if (injury.coord_x != null && injury.coord_y != null) {
                const isHovered = hoveredInjury === injury.id;
                return (
                  <g key={injury.id}>
                    {/* Point permanent */}
                    <circle
                      cx={injury.coord_x}
                      cy={injury.coord_y}
                      r={isHovered ? 2 : 2.2}
                      fill={isHovered ? '#ed0909' : '#f40909'}
                      stroke={isHovered ? '#0c0c0c' : '#080808'}
                      strokeWidth={isHovered ? '0.8' : '0.5'}
                      className="transition-all duration-200"
                    />
                    {isHovered && (
                      <>
                        {/* Pulsation autour du point */}
                        <circle
                          cx={injury.coord_x}
                          cy={injury.coord_y}
                          r={3}
                          fill="none"
                          stroke="#02fb2c"
                          strokeWidth="0.8"
                          opacity="0.2"
                        >
                          <animate
                            attributeName="r"
                            from="2"
                            to="8"
                            dur="1s"
                            repeatCount="indefinite"
                          />
                          <animate
                            attributeName="opacity"
                            from="0.8"
                            to="0"
                            dur="1s"
                            repeatCount="indefinite"
                          />
                        </circle>
                      </>
                    )}
                  </g>
                );
              }
              return null;
            })}
          </svg>
        </div>
      </div>

      {/* Colonne droite : Historique des blessures */}
      <div>
        <h3 className="font-semibold text-gray-700 mb-3 text-center">
          Historique des blessures ({injuries.length})
        </h3>
        
        {injuries.length === 0 ? (
          <div className="p-8 text-center bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
            <svg className="w-12 h-12 mx-auto text-gray-400 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="text-gray-500">Aucune blessure enregistrée</p>
            <p className="text-sm text-gray-400 mt-1">Cliquez sur l'image pour ajouter une blessure</p>
          </div>
        ) : (
          <div className="space-y-2 max-h-[600px] overflow-y-auto pr-2">
            {injuries.map((injury) => (
              <div
                key={injury.id}
                onMouseEnter={() => setHoveredInjury(injury.id)}
                onMouseLeave={() => setHoveredInjury(null)}
              >
                <div className="grid grid-cols-4 gap-4 divide-x divide-gray-300 items-center mb-4 p-4 bg-gray-50 rounded-lg border"
                  style={{gridTemplateColumns: "110px 200px 90px 60px"}}>
                  {/* Colonne 1 : Date blessure + commentaire */}
                  <div>
                    <div className="text-gray-900 font-semibold">Début d'arrêt</div>
                    <div className="px-0 font-medium text-blue-700 text-center pr-3">
                      {new Date(injury.injury_date).toLocaleDateString('fr-FR')}
                    </div>
                    <div className="text-sm text-gray-700 mt-2 text-center pr-2">{injury.comment}</div>
                  </div>

                  {/* Colonne 2 : Jusqu'au + restrictionDate / Le joueur + restrictionType */}
                  <div>
                    <div className="text-gray-900 font-semibold text-center pr-2">Jusqu'au</div>
                    <div className="font-medium text-blue-700 text-center pr-2">
                      {injury.restriction_date
                        ? new Date(injury.restriction_date).toLocaleDateString('fr-FR')
                        : "Pas de date"}
                    </div>
                    <div className="text-gray-900 font-semibold mt-2 text-center pr-2">Le joueur</div>
                    <div className="font-medium text-blue-700 text-center pr-3">
                      {(() => {
                        let colorClass = "";
                        switch (injury.restriction_type) {
                          case "no_sport":
                            colorClass = "border-red-500 text-red-700 bg-red-50";
                            break;
                          case "light_training":
                            colorClass = "border-yellow-400 text-yellow-700 bg-yellow-50";
                            break;
                          case "normal_play":
                            colorClass = "border-green-500 text-green-700 bg-green-50";
                            break;
                          default:
                            colorClass = "border-gray-300 text-gray-700 bg-gray-50";
                        }
                        const label = {
                          no_sport: "Ne peut pas faire d'activité sportive",
                          light_training: "Peut s'entraîner sans forcer",
                          normal_play: "Peut jouer normalement"
                        }[injury.restriction_type] || "Non renseigné";
                        return (
                          <span className={`inline-block px-2 py-1 rounded border font-semibold ${colorClass}`}>
                            {label}
                          </span>
                        );
                      })()}
                    </div>
                  </div>

                  {/* Colonne 3 : Fin d'arrêt + injury_end_date */}
                  <div>
                    <div className="text-gray-900 font-semibold text-center pr-3">Fin d'arrêt</div>
                    <div className="font-medium text-blue-700 mt-2 text-center pr-3">
                      {injury.injury_end_date
                        ? new Date(injury.injury_end_date).toLocaleDateString('fr-FR')
                        : "Pas de date"}
                    </div>
                  </div>

                  {/* Colonne 4 : Boutons */}
                  <div className="flex flex-col items-end gap-10 w-25 text-center pr-3">
                    <button
                      className="px-3 py-1 bg-yellow-400 text-white rounded hover:bg-yellow-600"
                      onClick={() => onEditInjury(injury)}
                    >
                      Modifier
                    </button>
                    <button
                      className="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-700"
                      onClick={e => handleDelete(e, injury.id)}
                    >
                      Supprimer
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
        <div className="col-span-full mt-5 p-4 bg-white rounded-lg text-center text-gray-900 font-medium">
          Ce joueur cumule {totalDays} jours d'arrêt
        </div>
      </div>
    </div>
  );
};

export default MedicalMap;
