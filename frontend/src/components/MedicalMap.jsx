import React, { useState, useRef } from 'react';

const MedicalMap = ({ onCoordinatesClick, injuries = [] }) => {
  const imageRef = useRef(null);
  const [hoveredInjury, setHoveredInjury] = useState(null);

  const handleImageClick = (e) => {
    if (!imageRef.current) return;

    const rect = imageRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;

    onCoordinatesClick?.({ coord_x: x, coord_y: y });
  };

  return (
    <div className="relative w-full max-w-2xl mx-auto">
      <div className="relative">
        <img
          ref={imageRef}
          src="/images/body-anatomy.jpg"
          alt="Anatomie du corps humain"
          className="w-full h-auto cursor-crosshair rounded-lg shadow-lg"
          onClick={handleImageClick}
        />
        
        {/* Overlay SVG pour afficher les marqueurs */}
        <svg
          className="absolute top-0 left-0 w-full h-full pointer-events-none"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
        >
          {/* Afficher les blessures existantes */}
          {injuries.map((injury) => {
            if (injury.coord_x != null && injury.coord_y != null) {
              const isHovered = hoveredInjury === injury.id;
              return (
                <g key={injury.id}>
                  <circle
                    cx={injury.coord_x}
                    cy={injury.coord_y}
                    r={isHovered ? 2 : 1.5}
                    fill={isHovered ? '#ef4444' : '#f87171'}
                    stroke={isHovered ? '#dc2626' : '#ef4444'}
                    strokeWidth={isHovered ? '0.5' : '0.3'}
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
                        stroke="#ef4444"
                        strokeWidth="0.4"
                        opacity="0.6"
                      >
                        <animate
                          attributeName="r"
                          from="2"
                          to="4"
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

      {/* Liste des blessures */}
      {injuries.length > 0 && (
        <div className="mt-6 space-y-2">
          <h3 className="font-semibold text-gray-700 mb-3">Historique des blessures</h3>
          {injuries.map((injury) => (
            <div
              key={injury.id}
              className="p-3 bg-white border border-gray-200 rounded-lg hover:shadow-md transition-shadow cursor-pointer"
              onMouseEnter={() => setHoveredInjury(injury.id)}
              onMouseLeave={() => setHoveredInjury(null)}
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
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
                {injury.coord_x != null && injury.coord_y != null && (
                  <div className="ml-2 text-xs text-gray-400">
                    📍
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default MedicalMap;
