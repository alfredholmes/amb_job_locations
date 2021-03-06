package com.alfred.jobModel;

import java.awt.Canvas;
import java.awt.Color;
import java.awt.Graphics;


public class Graph extends Canvas{
	/**
	 * 
	 */
	private static final long serialVersionUID = 2L;
	Model model;
	int width, height;
	public Graph(int width, int height, Model m) {
		this.width = width;
		this.height = height;
		setSize(width, height);
		setBackground(Color.white);
		model = m;
	}
	
	public void paint(Graphics g) {
		double min_rank = 1.0;
		for(City c : model.cities) {
			if(c.populationSize() < min_rank && c.populationSize() != 0) {
				min_rank = c.populationSize();
				
			}
				
		}
		for(City c: model.cities) {
			g.setColor(new Color((float)c.getIndustryMean(), (float)c.getIndustryVariance() < 1.0f ? (float)c.getIndustryVariance() : 1.0f , 1.0f - (float)c.getIndustryMean()));
			//System.out.println(c.population_position());
			circle(g, (int)(Math.log(c.populationRank()) / Math.log(model.cities.size()) * width), (int)((Math.log(c.populationSize()) /  Math.log(min_rank)) * height), 9);
		}
		
		
		g.setColor(Color.black);	
		g.drawLine(0, 0, 5 * (int)(width * (1 / Math.log(model.cities.size()))), - 5 * (int)(height * (1 / Math.log(min_rank))));
		
	}
	
	public void circle(Graphics g, int x, int y, int r) {
		int render_x = x - r;
		int render_y = y - r;
		g.fillOval(render_x, render_y, 2*r, 2*r);
	}
}
