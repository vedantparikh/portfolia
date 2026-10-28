const Card = ({ as: Tag = "div", className = "p-6", ...props }) => (
  <Tag className={`card ${className}`.trim()} {...props} />
);

export default Card;
