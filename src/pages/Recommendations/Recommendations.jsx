// pages/Recommendations/Recommendations.jsx
import React, { useState } from 'react';
import { useAppContext } from '../../context';
import './Recommendations.css';

const Recommendations = () => {
  const { state } = useAppContext();
  const { user, loading } = state;

  // State for toggling details
  const [expandedItems, setExpandedItems] = useState({});

  // Return blank while loading to keep it clean
  if (loading) {
    return <div className="content-section"></div>;
  }

  const toggleDetails = (itemId) => {
    setExpandedItems(prev => ({
      ...prev,
      [itemId]: !prev[itemId]
    }));
  };

  const renderExpandIcon = (itemId) => (
    <svg 
      className="expand-icon" 
      viewBox="0 0 24 24" 
      fill="currentColor" 
      onClick={() => toggleDetails(itemId)}
      style={{
        transform: expandedItems[itemId] ? 'rotate(180deg)' : 'rotate(0deg)'
      }}
    >
      <path d="M7 10l5 5 5-5z"/>
    </svg>
  );

  const dietRecommendations = [
    {
      id: 'fiber',
      title: 'Increase Fiber-Rich Foods',
      description: 'Include more whole grains, legumes, and vegetables in your diet.',
      reason: 'Supports <i>Ruminococcus bromii</i> growth',
      foods: [
        { name: 'Whole Oats', image: '/assets/images/food_lifestyle/oats.jpeg' },
        { name: 'Red Lentils', image: '/assets/images/food_lifestyle/lentils.jpeg' },
        { name: 'Broccoli', image: '/assets/images/food_lifestyle/brocolli.jpeg' }
      ],
      benefits: [
        'Promotes growth of beneficial bacteria',
        'Improves bowel regularity',
        'Helps manage blood sugar levels',
        'Supports weight management'
      ],
      tips: 'Aim for at least 25-30g of fiber daily. Increase intake gradually to allow your digestive system to adjust. Drink plenty of water with fiber-rich foods.'
    },
    {
      id: 'prebiotic',
      title: 'Add Prebiotic Foods',
      description: 'Incorporate garlic, onions, and leeks to support beneficial bacteria.',
      reason: 'Enhances <i>Faecalibacterium prausnitzii</i>',
      foods: [
        { name: 'Garlic', image: '/assets/images/food_lifestyle/garlic.jpeg' },
        { name: 'Onions', image: '/assets/images/food_lifestyle/onions.jpeg' },
        { name: 'Jerusalem Artichoke', image: '/assets/images/food_lifestyle/jersulam.jpeg' }
      ],
      benefits: [
        'Selectively feeds beneficial bacteria',
        'Increases production of short-chain fatty acids',
        'Strengthens gut barrier function',
        'Reduces inflammation in the digestive tract'
      ],
      tips: 'Cook with garlic and onions regularly, and try to include at least one prebiotic-rich food daily. Raw forms contain higher prebiotic content, but cooked versions still provide benefits.'
    }
  ];

  const lifestyleRecommendations = [
    {
      id: 'exercise',
      title: 'Regular Exercise',
      description: 'Aim for 30 minutes of moderate activity daily.',
      reason: 'Improves microbial diversity',
      activities: [
        { name: 'Brisk Walking', image: '/assets/images/food_lifestyle/walking.jpeg' },
        { name: 'Cycling', image: '/assets/images/food_lifestyle/cycling.jpeg' },
        { name: 'Swimming', image: '/assets/images/food_lifestyle/swimming.png' }
      ],
      benefits: [
        'Increases beneficial gut bacteria diversity',
        'Improves gut transit time',
        'Reduces gut inflammation',
        'Enhances immune function'
      ],
      tips: 'Start with 10-15 minutes daily if you\'re new to exercise, and gradually increase to 30 minutes. Consistency is more important than intensity. Try to exercise at least 5 days per week.'
    },
    {
      id: 'stress',
      title: 'Stress Management',
      description: 'Practice meditation or yoga for 15-20 minutes daily.',
      reason: 'Supports gut-brain axis',
      activities: [
        { name: 'Mindfulness Meditation', image: '/assets/images/food_lifestyle/meditation.png' },
        { name: 'Gentle Yoga', image: '/assets/images/food_lifestyle/yoga.png' },
        { name: 'Deep Breathing', image: '/assets/images/food_lifestyle/deepBreathing.jpeg' }
      ],
      benefits: [
        'Reduces stress hormones that disrupt gut function',
        'Improves vagal tone and gut motility',
        'Decreases intestinal permeability',
        'Supports balanced gut microbiome'
      ],
      tips: 'Start with just 5 minutes daily of your preferred stress-reduction technique. Use guided apps for meditation or yoga if you\'re a beginner. Consistency is key - aim for daily practice, ideally at the same time each day.'
    }
  ];

  const probioticProducts = [
    {
      id: 'bifidobacterium',
      title: 'Bifidobacterium Probiotic',
      description: 'Complex Probiotic Blend',
      reason: 'Not detected in sample',
      image: '/assets/images/probiotics_images/Bifidobacterium_Probiotic_Complex.jpeg',
      strains: [
        '<i>Bifidobacterium longum</i> (5 billion CFU)',
        '<i>Bifidobacterium bifidum</i> (3 billion CFU)',
        '<i>Bifidobacterium infantis</i> (2 billion CFU)',
        '<i>Bifidobacterium breve</i> (2 billion CFU)'
      ],
      details: 'A comprehensive probiotic formula specifically designed to restore and maintain healthy levels of <i>Bifidobacterium</i> in the gut microbiome. This blend supports digestive health, immune function, and helps maintain intestinal barrier integrity.',
      clinicalTrials: 'The specific strains in this formula have been researched in 12 clinical trials, demonstrating effectiveness for IBS symptom relief, improved digestive function, and enhanced immune response.',
      keyStudy: '"<i>Bifidobacterium</i> supplementation reduces inflammatory markers in subjects with metabolic syndrome" (Journal of Nutritional Science, 2023)',
      storage: 'Store in a cool, dry place below 25°C (77°F). Refrigeration recommended after opening to maintain potency. Shelf life: 24 months when sealed, 3 months after opening if refrigerated.'
    },
    {
      id: 'akkermansia',
      title: 'Akkermansia Probiotic',
      description: 'Gut Barrier Support',
      reason: 'Not detected in sample',
      image: '/assets/images/probiotics_images/Akkermansia_Probiotic_Blend.jpeg',
      strains: [
        '<i>Akkermansia muciniphila</i> (3 billion CFU)',
        '<i>Faecalibacterium prausnitzii</i> (2 billion CFU)',
        '<i>Roseburia intestinalis</i> (1 billion CFU)'
      ],
      details: 'A specialized probiotic formula containing <i>Akkermansia muciniphila</i>, a keystone species that supports the gut mucosal lining and helps maintain proper barrier function. This supplement is designed to improve metabolic health and gut integrity.',
      clinicalTrials: '<i>Akkermansia muciniphila</i> has been the subject of 8 human clinical trials, showing positive effects on metabolic parameters and gut barrier function. This specific formulation was evaluated in a 3-month study with 120 participants.',
      keyStudy: '"<i>Akkermansia muciniphila</i> supplementation improves metabolic parameters and reinforces gut barrier function" (Nature Metabolism, 2022)',
      storage: 'Refrigeration required (2-8°C or 35-46°F). Do not freeze. Keep away from moisture and direct sunlight. The specialized encapsulation technology maintains viability for 14 days at room temperature during shipping.'
    },
    {
      id: 'lactobacillus',
      title: 'Lactobacillus Blend',
      description: 'Digestive Health Support',
      reason: 'Low levels detected',
      image: '/assets/images/probiotics_images/Lactobacillus_Probiotic.jpeg',
      strains: [
        '<i>Lactobacillus acidophilus</i> (5 billion CFU)',
        '<i>Lactobacillus plantarum</i> (4 billion CFU)',
        '<i>Lactobacillus rhamnosus</i> (3 billion CFU)',
        '<i>Lactobacillus casei</i> (2 billion CFU)',
        '<i>Lactobacillus gasseri</i> (1 billion CFU)'
      ],
      details: 'A diverse <i>Lactobacillus</i> probiotic complex designed to enhance digestive function and immune health. This formula addresses occasional digestive discomfort, supports nutrient absorption, and helps maintain a balanced microbiome.',
      clinicalTrials: 'The <i>Lactobacillus</i> strains in this formula have been studied in over 20 clinical trials. Our specific blend has been evaluated in a 6-month study with 250 participants, showing significant improvements in digestive symptoms and immune markers.',
      keyStudy: '"Multi-strain <i>Lactobacillus</i> supplementation reduces digestive symptoms and inflammatory markers: A randomized controlled trial" (Gut Microbiome, 2023)',
      storage: 'Store in a cool, dry place below 25°C (77°F). No refrigeration necessary due to patented shelf-stable technology. Keep sealed until use. Best if used within 2 years of manufacture date.'
    },
    {
      id: 'bacillus',
      title: 'Bacillus Complex',
      description: 'Immune Support Blend',
      reason: 'Enhancement recommended',
      image: '/assets/images/probiotics_images/Bacillus_Probiotic.jpeg',
      strains: [
        '<i>Bacillus subtilis</i> (3 billion CFU)',
        '<i>Bacillus coagulans</i> (4 billion CFU)',
        '<i>Bacillus clausii</i> (2 billion CFU)',
        '<i>Bacillus licheniformis</i> (1 billion CFU)'
      ],
      details: 'A potent spore-forming probiotic formula featuring <i>Bacillus</i> species that can survive harsh digestive conditions. This formula supports immune function, protein digestion, and helps maintain a balanced microbiome even during periods of stress or antibiotic use.',
      clinicalTrials: 'The <i>Bacillus</i> strains in this formula have been studied in 15 clinical trials, with particular focus on immune function and microbiome resilience. Our specific combination has been validated in a 4-month study involving 180 participants.',
      keyStudy: '"<i>Bacillus</i>-based probiotics enhance immune resilience and microbiome stability during antibiotic therapy" (Frontiers in Immunology, 2023)',
      storage: 'Shelf-stable at room temperature due to the natural spore-forming properties of <i>Bacillus</i> species. Store in a cool, dry place below 30°C (86°F). Resistant to heat and humidity. Shelf life: 36 months when properly stored.'
    }
  ];

  const supplements = [
    {
      id: 'prebiotic-fiber',
      title: 'Prebiotic Fiber',
      description: 'Premium Inulin Complex',
      reason: 'Supports beneficial bacteria',
      image: '/assets/images/probiotics_images/Premium_Inulin_Fiber_Supplement.jpeg',
      ingredients: [
        'Organic Chicory Root Inulin (5g per serving)',
        'Jerusalem Artichoke Extract (2g per serving)',
        'Acacia Fiber (1g per serving)',
        'Green Banana Resistant Starch (1g per serving)'
      ],
      details: 'A premium blend of inulin and other soluble fibers that serve as food for beneficial gut bacteria. This prebiotic formula helps increase populations of <i>Bifidobacteria</i> and other beneficial microbes while supporting regular digestive function.',
      clinicalTrials: 'This prebiotic formula has been evaluated in 10 clinical trials, demonstrating significant increases in beneficial bacteria, particularly <i>Bifidobacteria</i> and <i>Faecalibacterium</i>, within 14 days of regular use.',
      keyStudy: '"Multi-component prebiotic fiber supplementation increases beneficial bacteria and improves markers of gut barrier function" (Microbiome, 2022)',
      storage: 'Store in a cool, dry place with container tightly closed. Protect from humidity and moisture. No refrigeration required. Best used within 2 years of manufacture date.'
    },
    {
      id: 'omega-3',
      title: 'Omega-3 Complex',
      description: 'High-Potency Fish Oil',
      reason: 'Reduces inflammation',
      image: '/assets/images/probiotics_images/High-Potency_Fish_Oil_Complex.jpeg',
      ingredients: [
        'Pure Triglyceride-form Fish Oil (1200mg per serving)',
        'EPA (Eicosapentaenoic Acid) (750mg per serving)',
        'DHA (Docosahexaenoic Acid) (550mg per serving)',
        'Mixed tocopherols (natural Vitamin E, 5 IU)',
        'Rosemary extract (natural preservative)'
      ],
      details: 'A high-potency, pharmaceutical-grade fish oil supplement providing concentrated EPA and DHA omega-3 fatty acids. This formula supports gut health by reducing inflammation, enhancing membrane integrity, and promoting a balanced inflammatory response.',
      clinicalTrials: 'This specific ratio of EPA and DHA has been studied in 18 clinical trials, with demonstrated effects on reducing inflammation markers and supporting gut barrier integrity. The triglyceride form offers superior absorption compared to ethyl ester forms.',
      keyStudy: '"High-dose EPA and DHA supplementation reduces intestinal permeability and inflammatory markers in patients with inflammatory bowel conditions" (Journal of Clinical Nutrition, 2022)',
      storage: 'Store in a cool, dark place, preferably refrigerated after opening. Keep tightly sealed and away from heat and light to prevent oxidation. Use within 90 days of opening.'
    },
    {
      id: 'vitamin-d',
      title: 'Vitamin D3',
      description: 'Immune Support Formula',
      reason: 'Essential nutrient',
      image: '/assets/images/probiotics_images/Vitamin_D_Complex.jpeg',
      ingredients: [
        'Vitamin D3 (Cholecalciferol) (5000 IU per serving)',
        'Vitamin K2 (MK-7) (100mcg per serving)',
        'Medium-chain triglyceride oil (MCT oil from coconut)',
        'Extra virgin olive oil'
      ],
      details: 'A premium vitamin D3 (cholecalciferol) supplement with added vitamin K2 for optimal calcium utilization and immune support. This formula helps regulate immune function in the gut and supports the integrity of the intestinal barrier.',
      clinicalTrials: 'This vitamin D3+K2 combination has been evaluated in 12 clinical trials focusing on immune function and gut health. Research shows that vitamin D receptors in the gut play a critical role in modulating the microbiome and immune response.',
      keyStudy: '"Vitamin D supplementation improves gut barrier function and modulates microbiome composition in vitamin D-deficient individuals" (Frontiers in Immunology, 2023)',
      storage: 'Store in a cool, dry place away from direct sunlight. No refrigeration required. Keep tightly closed when not in use. Shelf life: 24 months from manufacture date.'
    },
    {
      id: 'zinc',
      title: 'Zinc Complex',
      description: 'Mineral Support Blend',
      reason: 'Immune support',
      image: 'assets/images/probiotics_images/Zinc_Complex.jpeg',
      ingredients: [
        'Zinc Bisglycinate (15mg elemental zinc)',
        'Zinc Citrate (10mg elemental zinc)',
        'Zinc Picolinate (5mg elemental zinc)',
        'Copper Bisglycinate (2mg, for zinc balance)',
        'Selenium (50mcg as selenomethionine)'
      ],
      details: 'A highly bioavailable zinc formula utilizing multiple forms of zinc for optimal absorption and utilization. This supplement supports immune function, intestinal barrier integrity, and protein synthesis involved in tissue repair.',
      clinicalTrials: 'This multi-form zinc complex has been studied in 9 clinical trials focused on immune function and digestive health. Research demonstrates zinc\'s critical role in maintaining tight junction proteins in the intestinal lining.',
      keyStudy: '"Optimized zinc supplementation improves intestinal permeability markers and enhances microbiome diversity in subjects with zinc deficiency" (Journal of Trace Elements in Medicine and Biology, 2023)',
      storage: 'Store in a cool, dry place below 25°C (77°F). Keep bottle tightly closed to protect from moisture. No refrigeration required. Best used within 24 months of manufacture date.'
    }
  ];

  return (
    <div id="recommendations" className="content-section">
      <div className="page-title-container">
        <h1 className="page-title">Personalized Recommendations</h1>
        <div className="last-updated">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"></circle>
            <polyline points="12 6 12 12 16 14"></polyline>
          </svg>
          Last updated: {user.lastUpdated}
        </div>
      </div>
      
      <div className="recommendations-container">
        {/* Summary Panel */}
        <div className="summary-panel">
          <h2 className="summary-title">Your Personalized Recommendations</h2>
          <p className="summary-content">
            Based on your microbiome analysis (ID: {user.reportId}), we've identified several key areas for optimization. Your gut microbiome shows high diversity (Shannon alpha div. &gt; 3), which is positive. However, some beneficial species could be enhanced through targeted interventions.
          </p>
        </div>

        {/* Recommendations Grid */}
        <div className="recommendations-grid">
          {/* Diet Recommendations */}
          <div className="recommendation-card">
            <div className="card-header">
              <svg className="card-icon" viewBox="0 0 24 24" fill="none" stroke="#00BFA5">
                <path d="M3 6h18M3 12h18M3 18h18"/>
              </svg>
              <h2 className="card-title">Dietary Recommendations</h2>
            </div>
            <ul className="recommendation-list">
              {dietRecommendations.map((item) => (
                <li key={item.id} className="recommendation-item">
                  <div className="item-content">
                    <div className="item-title-container">
                      <div className="item-title">{item.title}</div>
                      {renderExpandIcon(item.id)}
                    </div>
                    <div className="item-description">{item.description}</div>
                    <span className="reason-tag">{item.reason}</span>
                    
                    <div className={`product-details ${expandedItems[item.id] ? 'active' : ''}`}>
                      <div className="detail-section">
                        <div className="detail-title">Recommended Foods</div>
                        <div className="detail-content">
                          These fiber-rich foods are particularly effective at supporting beneficial gut bacteria and improving digestive health.
                        </div>
                        <div className="food-grid">
                          {item.foods.map((food, index) => (
                            <div key={index} className="food-item">
                              <img src={food.image} alt={food.name} className="food-image" />
                              <div className="food-name">{food.name}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div className="detail-section">
                        <div className="detail-title">Health Benefits</div>
                        <ul className="detail-list">
                          {item.benefits.map((benefit, index) => (
                            <li key={index}>{benefit}</li>
                          ))}
                        </ul>
                      </div>
                      <div className="detail-section">
                        <div className="detail-title">Dietary Tips</div>
                        <div className="detail-content">{item.tips}</div>
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          {/* Lifestyle Recommendations */}
          <div className="recommendation-card">
            <div className="card-header">
              <svg className="card-icon" viewBox="0 0 24 24" fill="none" stroke="#00BFA5">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
              </svg>
              <h2 className="card-title">Lifestyle Changes</h2>
            </div>
            <ul className="recommendation-list">
              {lifestyleRecommendations.map((item) => (
                <li key={item.id} className="recommendation-item">
                  <div className="item-content">
                    <div className="item-title-container">
                      <div className="item-title">{item.title}</div>
                      {renderExpandIcon(item.id)}
                    </div>
                    <div className="item-description">{item.description}</div>
                    <span className="reason-tag">{item.reason}</span>
                    
                    <div className={`product-details ${expandedItems[item.id] ? 'active' : ''}`}>
                      <div className="detail-section">
                        <div className="detail-title">Recommended Activities</div>
                        <div className="detail-content">
                          These activities are particularly beneficial for gut health and overall well-being.
                        </div>
                        <div className="food-grid">
                          {item.activities.map((activity, index) => (
                            <div key={index} className="food-item">
                              <img src={activity.image} alt={activity.name} className="food-image" />
                              <div className="food-name">{activity.name}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div className="detail-section">
                        <div className="detail-title">Health Benefits</div>
                        <ul className="detail-list">
                          {item.benefits.map((benefit, index) => (
                            <li key={index}>{benefit}</li>
                          ))}
                        </ul>
                      </div>
                      <div className="detail-section">
                        <div className="detail-title">Implementation Tips</div>
                        <div className="detail-content">{item.tips}</div>
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          {/* Probiotic Support */}
          <div className="recommendation-card">
            <div className="card-header">
              <svg className="card-icon" viewBox="0 0 24 24" fill="none" stroke="#00BFA5">
                <circle cx="12" cy="12" r="10"/>
                <path d="M12 16v-4M12 8h.01"/>
              </svg>
              <h2 className="card-title">Probiotic Support</h2>
            </div>
            <div className="products-grid">
              {probioticProducts.map((product) => (
                <div key={product.id} className="product-card">
                  <div className="product-info">
                    <img src={product.image} alt={product.title} className="product-thumb"/>
                    <div>
                      <div className="item-title-container">
                        <div className="item-title">{product.title}</div>
                        {renderExpandIcon(product.id)}
                      </div>
                      <div className="item-description">{product.description}</div>
                      <span className="reason-tag" dangerouslySetInnerHTML={{ __html: product.reason }}></span>
                    </div>
                  </div>
                  <div className={`product-details ${expandedItems[product.id] ? 'active' : ''}`}>
                    <div className="detail-section">
                      <div className="detail-title">Description</div>
                      <div className="detail-content" dangerouslySetInnerHTML={{ __html: product.details }}></div>
                    </div>
                    <div className="detail-section">
                      <div className="detail-title">Probiotic Strains</div>
                      <ul className="detail-list">
                        {product.strains.map((strain, index) => (
                          <li key={index} dangerouslySetInnerHTML={{ __html: strain }}></li>
                        ))}
                      </ul>
                    </div>
                    <div className="detail-section">
                      <div className="detail-title">Clinical Trials</div>
                      <div className="detail-content" dangerouslySetInnerHTML={{ __html: product.clinicalTrials }}></div>
                      <div className="trials-info" dangerouslySetInnerHTML={{ __html: product.keyStudy }}></div>
                    </div>
                    <div className="detail-section">
                      <div className="detail-title">Storage Instructions</div>
                      <div className="detail-content" dangerouslySetInnerHTML={{ __html: product.storage }}></div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Supplement Recommendations */}
          <div className="recommendation-card">
            <div className="card-header">
              <svg className="card-icon" viewBox="0 0 24 24" fill="none" stroke="#00BFA5">
                <circle cx="12" cy="12" r="10"/>
                <path d="M8 14s1.5 2 4 2 4-2 4-2"/>
              </svg>
              <h2 className="card-title">Supplement Recommendations</h2>
            </div>
            <div className="products-grid">
              {supplements.map((supplement) => (
                <div key={supplement.id} className="product-card">
                  <div className="product-info">
                    <img src={supplement.image} alt={supplement.title} className="product-thumb"/>
                    <div>
                      <div className="item-title-container">
                        <div className="item-title">{supplement.title}</div>
                        {renderExpandIcon(supplement.id)}
                      </div>
                      <div className="item-description">{supplement.description}</div>
                      <span className="reason-tag">{supplement.reason}</span>
                    </div>
                  </div>
                  <div className={`product-details ${expandedItems[supplement.id] ? 'active' : ''}`}>
                    <div className="detail-section">
                      <div className="detail-title">Description</div>
                      <div className="detail-content" dangerouslySetInnerHTML={{ __html: supplement.details }}></div>
                    </div>
                    <div className="detail-section">
                      <div className="detail-title">Key Ingredients</div>
                      <ul className="detail-list">
                        {supplement.ingredients.map((ingredient, index) => (
                          <li key={index}>{ingredient}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="detail-section">
                      <div className="detail-title">Clinical Trials</div>
                      <div className="detail-content" dangerouslySetInnerHTML={{ __html: supplement.clinicalTrials }}></div>
                      <div className="trials-info" dangerouslySetInnerHTML={{ __html: supplement.keyStudy }}></div>
                    </div>
                    <div className="detail-section">
                      <div className="detail-title">Storage Instructions</div>
                      <div className="detail-content">{supplement.storage}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Recommendations;