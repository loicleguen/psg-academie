import React, { useState, useRef } from 'react';

const MedicalMap = ({ onCoordinatesClick, onDeleteInjury, onEditInjury, injuries = [] }) => {
  const imageRef = useRef(null);
  const [hoveredInjury, setHoveredInjury] = useState(null);

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

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Colonne gauche : Image du corps */}
      <div className="relative">
        <h3 className="font-semibold text-gray-700 mb-3">Cliquez sur la zone blessée</h3>
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
        <h3 className="font-semibold text-gray-700 mb-3">
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
                className="p-3 bg-white border border-gray-200 rounded-lg hover:shadow-md hover:border-blue-300 transition-all cursor-pointer relative group"
                onMouseEnter={() => setHoveredInjury(injury.id)}
                onMouseLeave={() => setHoveredInjury(null)}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1 pr-8">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-900">
                        {new Date(injury.injury_date).toLocaleDateString('fr-FR')}
                      </span>
                      {injury.body_part && (
                        <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full">
                          {injury.body_part}
                        </span>
                      )}
                    </div>
                    {injury.comment && (
                      <p className="mt-1 text-sm text-gray-600">{injury.comment}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {injury.coord_x != null && injury.coord_y != null ? (
                      <div className="text-xs text-green-500" title="Position enregistrée">
                        📍
                      </div>
                    ) : (
                      <div className="text-xs text-gray-300" title="Position non enregistrée">
                        📍
                      </div>
                    )}
                    <div className="flex flex-col items-end gap-1">
                      <button
                        className="mb-1 px-2 py-1 text-xs bg-yellow-400 text-white rounded hover:bg-yellow-600"
                        title="Modifier cette blessure"
                        onClick={() => onEditInjury?.(injury)}
                      >
                        Modifier
                      </button>
                      {/* Bouton de suppression */}
                      <button
                        className="mb-1 px-2 py-1 text-xs bg-red-400 text-white rounded hover:bg-red-800"
                        title="Supprimer cette blessure"
                        onClick={(e) => handleDelete(e, injury.id)}
                      >
                        Supprimer
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default MedicalMap;
