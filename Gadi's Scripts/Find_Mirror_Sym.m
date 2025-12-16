function [ ang ] = Find_Mirror_Sym( X, Y )
%FIND_MIROR_SYM Summary of this function goes here
%   Detailed explanation goes here

% Transposes X adn Y vectors
X=X';
Y=Y';
Shape2D = [X;Y];

% Rotates the shape 85 deg clockwise from original positioning
% assumed to be manual-conventional 
% Shape = [X;Y];
% ang = deg2rad(80);
% R = [cos(-ang), -sin(-ang); sin(-ang), cos(-ang)]; %clockwise
% Shape = R*Shape;
% clear ang R

% plots initial position (using scatter as the poinits ar unsorted yet)
%f = figure();
%f = scatter(Shape(1,:),Shape(2,:));
%drawnow;
%pause(1);

%Rotates 170 counter clockwise and builds target function
for a = 1:360
    ang = deg2rad(a);
    R = [cos(ang), -sin(ang); sin(ang), cos(ang)]; %counter clockwise
    Rshape = R*Shape2D;
    
    X=Rshape(1,:);
    Y=Rshape(2,:);
       
    %devides shape into negatives and positive halves
    k=1; j=1;
    for i = 1:length(X)
        if X(i) > 0 
            Xpos(j) = X(i);
            Ypos(j) = Y(i);
            j = j+1;
        else
            Xneg(k) = X(i);
            Yneg(k) = Y(i);
            k = k+1;
        end
    end
    clear j k 
    
    %sorts each half
    [Yneg, IndNeg] = sort(Yneg);
    Xneg = Xneg(IndNeg);
    [Ypos, IndPos] = sort(Ypos);
    Xpos = Xpos(IndPos);
    clear IndNeg IndPos
    
    if size(Xneg,2) < size(Xpos,2)
        SamPoints = floor(0.8*size(Xneg,2));
    else
        SamPoints = floor(0.8*size(Xpos,2));
    end
    
    %samples 150 points in each half
    b = 0;
    j = 1;
    for i = 1:length(Yneg)/SamPoints:length(Yneg)
        if floor(i) > b
            b = floor(i);
            YnegS(j) = Yneg(b);
            XnegS(j) = Xneg(b);
            j = j + 1;
        end
    end
    clear Xneg Yneg
    Xneg = XnegS;
    Yneg = YnegS;
    clear XnegS YnegS
    
    b = 0;
    j = 1;
    for i = 1:length(Ypos)/SamPoints:length(Ypos)
        if floor(i) > b
            b = floor(i);
            YposS(j) = Ypos(b);
            XposS(j) = Xpos(b);
            j = j + 1;
        end
    end
    clear Xpos Ypos b j
    Xpos = XposS;
    Ypos = YposS;
    clear XposS YposS
    
    % mirrors negative half
    XnegF = -Xneg;
    
    %calcultes target function for this angle
    Dist = sqrt(((Ypos-Yneg).^2+(Xpos-XnegF).^2));
    SymInd(1,a) = sum(Dist,2);
    SymInd(2,a) = a;
    %plots rotation
    %cla(f, 'reset');
    %f=plot([Xneg, flip(Xpos)],[Yneg, flip(Ypos)]);
    %drawnow;
    %pause(0.05);
%     plot(ax1,Rshape(1,:),Rshape(2,:),'r');
%     drawnow
%     h=msgbox(num2str(SymInd(1,a)));
%     waitfor(h);
    clearvars Dist XnegF Xpos Ypos SamPoints X Y R Rshape
 end

%finds angle of minimal target function (i.e. max mirror symmetry)
ang = find(SymInd(1,:) == min(SymInd(1,:)));
% ang = ang - 85;
% ang = deg2rad(ang);
% R = [cos(ang), -sin(ang); sin(ang), cos(ang)]; %clockwise
% Rshape = R*Shape;
% Shape = Rshape;
% clear a R Rshape

%plots final position
%cla(f, 'reset');
%f=plot(Shape(1,:),Shape(2,:));
%ang = rad2deg(ang);
%drawnow;

end

